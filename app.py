import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Sales & Stock Intelligence Tool",
    layout="wide"
)

st.title("📊 Sales & Stock Intelligence Tool")

# =========================
# SIDEBAR - UPLOAD
# =========================
st.sidebar.header("📂 Upload Reports")

report1 = st.sidebar.file_uploader(
    "Report 1 (Stock)",
    type=["xlsx"]
)

report129 = st.sidebar.file_uploader(
    "Report 129 (Sales)",
    type=["xlsx"]
)

# =========================
# MAIN PROCESS
# =========================
if report1 and report129:

    # =========================
    # LOAD FILES
    # =========================
    df_stock = pd.read_excel(report1)
    df_sales = pd.read_excel(report129)

    # =========================
    # CLEAN COLUMN NAMES
    # =========================
    df_stock.columns = df_stock.columns.str.strip()
    df_sales.columns = df_sales.columns.str.strip()

    # =========================
    # RENAME COLUMNS
    # =========================
    df_stock.rename(
        columns={
            "Specialcode1": "SpecialCode",
            "Merch Group": "MerchGroup",
            "Merch Sub Group": "SubGroup",
            "Line": "Line",
            "Total Stock": "StockQty",
            "YasakliMi": "Blocked",
            "Buyer Group": "BuyerGroup",
            "UrunKlasman": "Classification",
            "EtiketTip": "EtiketTip"
        },
        inplace=True
    )

    df_sales.rename(
        columns={
            "Special Code": "SpecialCode",
            "Quantity": "SalesQty",
            "Price": "Price",
            "RenkKodu": "Color"
        },
        inplace=True
    )

    # =========================
    # STOCK AGGREGATION
    # =========================
    agg_dict = {
        "MerchGroup": "first",
        "SubGroup": "first",
        "Line": "first",
        "BuyerGroup": "first",
        "Classification": "first",
        "EtiketTip": "first",
        "Blocked": "max",
        "StockQty": "sum"
    }

    # Keep only existing columns
    agg_dict = {
        k: v
        for k, v in agg_dict.items()
        if k in df_stock.columns
    }

    # Add Cash column if exists
    if "Cash" in df_stock.columns:
        agg_dict["Cash"] = "mean"

    # Aggregate stock
    df_stock = (
        df_stock
        .groupby("SpecialCode")
        .agg(agg_dict)
        .reset_index()
    )

    # =========================
    # SALES PROCESSING
    # =========================
    df_sales["Date"] = pd.to_datetime(
        df_sales["Date"],
        errors="coerce"
    )

    today = pd.to_datetime(datetime.today())

    # Last 7 Days
    df_sales_7d = df_sales[
        df_sales["Date"] >= (today - pd.Timedelta(days=7))
    ]

    # Keep positive sales only
    df_sales_7d = df_sales_7d[
        df_sales_7d["SalesQty"] > 0
    ]

    # Revenue
    df_sales_7d["Revenue"] = (
        df_sales_7d["SalesQty"] *
        df_sales_7d["Price"]
    )

    # Group Sales
    sales_group = (
        df_sales_7d
        .groupby("SpecialCode")
        .agg(
            SalesQty_7D=("SalesQty", "sum"),
            Revenue=("Revenue", "sum")
        )
        .reset_index()
    )

    # =========================
    # COLOR EXTRACTION
    # =========================
    color_map = (
        df_sales
        .groupby("SpecialCode")["Color"]
        .agg(
            lambda x: (
                x.mode()[0]
                if not x.mode().empty
                else ""
            )
        )
        .reset_index()
    )

    # =========================
    # MERGE DATA
    # =========================
    df = pd.merge(
        df_stock,
        sales_group,
        on="SpecialCode",
        how="left"
    )

    df = pd.merge(
        df,
        color_map,
        on="SpecialCode",
        how="left"
    )

    # Fill missing values
    df.fillna(
        {
            "SalesQty_7D": 0,
            "Revenue": 0
        },
        inplace=True
    )

    # =========================
    # KPI CALCULATIONS
    # =========================
    df["Stock Cover"] = (
        df["StockQty"] /
        (df["SalesQty_7D"] / 7 + 0.01)
    )

    # Seller Tag
    def seller_tag(qty):

        if qty >= 20:
            return "🔥 Best Seller"

        elif qty <= 2:
            return "💀 Worst Seller"

        else:
            return "⚖️ Average"

    df["SellerTag"] = df["SalesQty_7D"].apply(seller_tag)

    # Ranking
    df["Rank"] = df["SalesQty_7D"].rank(
        method="dense",
        ascending=False
    )

    # =========================
    # FILTERS
    # =========================
    merch_filter = st.selectbox(
        "Filter by Merch Group",
        ["All"] +
        sorted(
            df["MerchGroup"]
            .dropna()
            .unique()
            .tolist()
        )
    )

    if merch_filter != "All":
        df = df[
            df["MerchGroup"] == merch_filter
        ]

    # =========================
    # ANALYSIS FUNCTION
    # =========================
    def build_analysis(group_cols, title):

        st.subheader(title)

        table = (
            df
            .groupby(group_cols)
            .agg(
                Sales=("SalesQty_7D", "sum"),
                Revenue=("Revenue", "sum"),
                Stock=("StockQty", "sum")
            )
            .reset_index()
        )

        table["Stock Cover"] = (
            table["Stock"] /
            (table["Sales"] / 7 + 0.01)
        )

        st.dataframe(
            table.sort_values(
                by="Sales",
                ascending=False
            ),
            hide_index=True
        )

    # =========================
    # ANALYSIS TABLES
    # =========================
    build_analysis(
        ["MerchGroup", "SubGroup"],
        "📊 Analysis: Merch+SubGroup"
    )

    if "BuyerGroup" in df.columns:

        build_analysis(
            ["MerchGroup", "BuyerGroup"],
            "📊 Analysis: Merch+Buyer Group"
        )

    build_analysis(
        ["MerchGroup", "Line"],
        "📊 Analysis: Merch+Line"
    )

    # =========================
    # DISPLAY COLUMNS
    # =========================
    cols_display = [
        "SpecialCode",
        "MerchGroup",
        "SubGroup",
        "BuyerGroup",
        "Classification",
        "Color",
        "SalesQty_7D",
        "StockQty",
        "Stock Cover"
    ]

    # =========================
    # TOP SELLERS
    # =========================
    st.subheader("📊 Top 10 Best Sellers")

    st.dataframe(
        df.sort_values(
            by="SalesQty_7D",
            ascending=False
        )
        .head(10)[cols_display],
        hide_index=True
    )

    # =========================
    # WORST SELLERS
    # =========================
    st.subheader("📉 Top 10 Worst Sellers")

    st.dataframe(
        df.sort_values(
            by="SalesQty_7D",
            ascending=True
        )
        .head(10)[cols_display],
        hide_index=True
    )

    # =========================
    # PRODUCT VIEW
    # =========================
    st.markdown("---")
    st.header("🧥 Product View")

    selected_product = st.selectbox(
        "Select Product",
        df["SpecialCode"].unique()
    )

    # =========================
    # PRODUCT DETAILS
    # =========================
    if selected_product:

        p = df[
            df["SpecialCode"] == selected_product
        ].iloc[0]

        clean_code = str(selected_product).replace(" ", "")

        # =========================
        # SUBGROUP MAPPING
        # =========================
        sub_map = {
            "BG": "Women",
            "BU": "Men",
            "CK": "Girls",
            "CU": "Boys",
            "EV": "Home",
            "ST": "Non-standard"
        }

        target = sub_map.get(
            p["SubGroup"],
            "Unknown"
        )

        price = p["Cash"] if "Cash" in p else 0

        # =========================
        # LAYOUT
        # =========================
        col1, col2 = st.columns(2)

        # =========================
        # LEFT SIDE
        # =========================
        with col1:

            st.write(f"Code: {selected_product}")

            st.write(
                f"Price: {round(price, 2)}"
            )

            st.info(f"👤 Target: {target}")

            st.success(
                f"Performance: {p['SellerTag']}"
            )

            st.info(
                f"📦 Stock: {p['StockQty']}"
            )

            st.info(
                f"📈 Sales 7D: {p['SalesQty_7D']}"
            )

            st.info(
                f"💰 Revenue: {round(p['Revenue'], 2)}"
            )

            st.info(
                f"📊 Stock Cover: {round(p['Stock Cover'], 2)}"
            )

            st.info(
                f"🏆 Rank: #{int(p['Rank'])}"
            )

            # =========================
            # LCW PRODUCT LINK
            # =========================
            lcw_url = (
                f"https://www.lcwaikiki.fr/recherche?q={clean_code}"
            )

            st.link_button(
                "🧥 See Product Image (LC Waikiki)",
                lcw_url
            )

        # =========================
        # RIGHT SIDE
        # =========================
        with col2:

            query = (
                f"{p['Classification']} "
                f"fashion DeFacto Kiabi "
                f"Koton Zara Bershka Shein"
            )

            q = urllib.parse.quote(query)

            st.link_button(
                "🖼 Compare Images",
                f"https://www.google.com/search?tbm=isch&q={q}"
            )

            st.link_button(
                "💰 Compare Prices",
                f"https://www.google.com/search?tbm=shop&q={q}"
            )

        # =========================
        # AI BENCHMARK
        # =========================
        st.subheader("🧠 AI Benchmark Analysis")

        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        if OPENAI_API_KEY:

            from openai import OpenAI

            client = OpenAI(
                api_key=OPENAI_API_KEY
            )

            if st.button("Run AI Benchmark"):

                prompt = f"""
SubMerch Mapping:
BG=Women
BU=Men
CK=Girls
CU=Boys
EV=Home
ST=Non-standard

Product:
SubGroup: {p['SubGroup']} ({target})
Classification: {p['Classification']}
Price: {price}
Sales: {p['SalesQty_7D']}
Stock: {p['StockQty']}
Stock Cover: {round(p['Stock Cover'], 2)}
Performance: {p['SellerTag']}
Rank: {int(p['Rank'])}

Compare with:
- DeFacto
- Kiabi
- Koton
- Zara
- Bershka
- Shein

Provide:
1. Price positioning
2. Style level
3. Trend alignment
4. Competitor comparison table
5. Final action

Keep concise and business-oriented.
"""

                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                st.success(
                    response
                    .choices[0]
                    .message
                    .content
                )

        else:
            st.info(
                "⚠️ Add OPENAI_API_KEY to enable AI"
            )

# =========================
# NO FILES
# =========================
else:

    st.info(
        "⬅️ Upload both reports to start"
    )