import re
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import pdfplumber
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Credit Card Expense Analyzer",
    page_icon="💳",
    layout="wide"
)


CATEGORY_RULES = {
    "Groceries": [
        "COSTCO", "KING SOOPERS", "SAFEWAY", "WAL-MART", "WALMART",
        "WM SUPERCENTER", "WHOLEFDS", "WHOLE FOODS", "FRESH MARKET",
        "ARASH", "ALMUSTAFA", "MECCA GROCERY", "LAXMI FOOD",
        "RESTAURANT DEPOT"
    ],
    "Restaurants / Coffee": [
        "QDOBA", "PANDA", "STARBUCKS", "IN-N-OUT", "PARIS BAGUETTE",
        "YEMEN GRILL", "SUMAC", "QAMARIA", "FELFEL", "HUMMUS",
        "RESTAURANT", "TST*", "PAYPAL *PANDA"
    ],
    "Gas / Parking / Transportation": [
        "SHELL", "PHILLIPS", "MAVERIK", "PARKWHIZ", "METROPOLIS",
        "PUBLIC WORKS-PRKG", "PARKING"
    ],
    "Insurance": [
        "PROGRESSIVE"
    ],
    "Online Shopping": [
        "EBAY", "PAYPAL *EBAY", "AMZ", "AMAZON", "BESTBUYCOM",
        "WWW COSTCO COM", "QINK", "TRYAURELA"
    ],
    "Online Subscriptions": [
        "OPENAI", "CHATGPT", "CLAUDE", "GOOGLE WORKSPACE",
        "GOOGLE MOODLOG", "APPLE.COM", "RING", "OPUS CLIP",
        "NAME-CHEAP", "NAMECHEAP", "HONEYTOON", "USP*COMIC"
    ],
    "Shopping": [
        "ROSS", "TARGET", "DOLLARTREE", "DOLLAR TREE", "FIVE BELOW",
        "WALGREENS"
    ],
    "Home / Tools": [
        "ACE", "TAMARAC SQUARE ACE", "MEGA HOME"
    ],
    "Medical / Health": [
        "DH EPIC", "HOSP", "CLINIC", "WALGREENS"
    ],
    "Travel / Entertainment": [
        "GREAT WOLF", "LODGE"
    ],
    "Business / Services": [
        "USPS", "POST OFFICE"
    ],
    "Laundry": [
        "LAVANDERIA", "LAUNDRY"
    ]
}


PAYMENT_CREDIT_KEYWORDS = [
    "PAYMENT FROM CHK",
    "ONLINE/MOBILE RECURRING FROM CHK",
    "PAYMENT",
]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_pdf_text(uploaded_file) -> str:
    text_parts = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)

    return "\n".join(text_parts)


def parse_transactions(text: str) -> pd.DataFrame:
    """
    Extracts transaction rows from Bank of America PDF text.

    Expected format:
    MM/DD MM/DD DESCRIPTION ... AMOUNT

    This parser is built for statements similar to:
    Transaction Date | Posting Date | Description | Amount
    """

    transactions = []

    lines = text.splitlines()

    for raw_line in lines:
        line = clean_text(raw_line)

        pattern = r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})$"
        match = re.match(pattern, line)

        if not match:
            continue

        trans_date, post_date, description, amount = match.groups()

        amount = float(amount.replace(",", ""))

        transactions.append({
            "transaction_date_raw": trans_date,
            "posting_date_raw": post_date,
            "description": description.strip(),
            "amount": amount
        })

    if not transactions:
        return pd.DataFrame(columns=[
            "transaction_date", "posting_date", "description", "amount"
        ])

    df = pd.DataFrame(transactions)
    return df


def attach_year(df: pd.DataFrame, selected_year: int) -> pd.DataFrame:
    df = df.copy()

    df["transaction_date"] = pd.to_datetime(
        df["transaction_date_raw"] + f"/{selected_year}",
        format="%m/%d/%Y",
        errors="coerce"
    )

    df["posting_date"] = pd.to_datetime(
        df["posting_date_raw"] + f"/{selected_year}",
        format="%m/%d/%Y",
        errors="coerce"
    )

    return df


def is_payment_or_credit(description: str, amount: float) -> bool:
    desc = description.upper()

    if amount < 0:
        return True

    return any(keyword in desc for keyword in PAYMENT_CREDIT_KEYWORDS)


def categorize_transaction(description: str) -> str:
    desc = description.upper()

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword.upper() in desc:
                return category

    return "Other / Unknown"


def filter_by_month(df: pd.DataFrame, selected_year: int, selected_month: int) -> pd.DataFrame:
    start_date = pd.Timestamp(date(selected_year, selected_month, 1))

    if selected_month == 12:
        end_date = pd.Timestamp(date(selected_year + 1, 1, 1))
    else:
        end_date = pd.Timestamp(date(selected_year, selected_month + 1, 1))

    return df[
        (df["transaction_date"] >= start_date) &
        (df["transaction_date"] < end_date)
    ].copy()


def money(value: float) -> str:
    return f"${value:,.2f}"


st.title("Credit Card Expense Analyzer")

st.write(
    "Upload one or more credit card PDF statements. "
    "The app filters by transaction date, categorizes expenses, and shows monthly totals."
)

uploaded_files = st.file_uploader(
    "Upload PDF statements",
    type=["pdf"],
    accept_multiple_files=True
)

col1, col2, col3 = st.columns(3)

with col1:
    selected_year = st.number_input(
        "Year",
        min_value=2020,
        max_value=2035,
        value=2026,
        step=1
    )

with col2:
    selected_month = st.selectbox(
        "Month",
        options=list(range(1, 13)),
        index=3,
        format_func=lambda x: datetime(2000, x, 1).strftime("%B")
    )

with col3:
    include_credits = st.checkbox(
        "Include refunds/credits in net total",
        value=True
    )

if uploaded_files:
    all_transactions = []

    for uploaded_file in uploaded_files:
        text = extract_pdf_text(uploaded_file)
        df = parse_transactions(text)

        if not df.empty:
            df["source_file"] = uploaded_file.name
            all_transactions.append(df)

    if not all_transactions:
        st.error("No transactions found. Try another PDF or check if the statement text is selectable.")
        st.stop()

    df_all = pd.concat(all_transactions, ignore_index=True)
    df_all = attach_year(df_all, selected_year)

    df_month = filter_by_month(df_all, selected_year, selected_month)

    if df_month.empty:
        st.warning("No transactions found for the selected month.")
        st.stop()

    df_month["is_payment_or_credit"] = df_month.apply(
        lambda row: is_payment_or_credit(row["description"], row["amount"]),
        axis=1
    )

    purchases_df = df_month[df_month["amount"] > 0].copy()
    purchases_df["category"] = purchases_df["description"].apply(categorize_transaction)

    credits_df = df_month[df_month["amount"] < 0].copy()
    credits_total = credits_df["amount"].sum()

    gross_spending = purchases_df["amount"].sum()

    if include_credits:
        net_spending = gross_spending + credits_total
    else:
        net_spending = gross_spending

    st.subheader("Monthly Summary")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Gross Spending", money(gross_spending))
    metric2.metric("Credits / Refunds", money(credits_total))
    metric3.metric("Net Spending", money(net_spending))
    metric4.metric("Transactions", len(purchases_df))

    st.divider()

    category_summary = (
        purchases_df
        .groupby("category", as_index=False)
        .agg(
            total=("amount", "sum"),
            count=("amount", "count")
        )
        .sort_values("total", ascending=False)
    )

    st.subheader("Spending by Category")

    col_chart, col_table = st.columns([1.2, 1])

    with col_chart:
        fig = px.pie(
            category_summary,
            names="category",
            values="total",
            title="Category Share"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        display_summary = category_summary.copy()
        display_summary["total"] = display_summary["total"].apply(money)
        st.dataframe(display_summary, use_container_width=True)

    st.divider()

    st.subheader("Largest Transactions")

    top_n = st.slider("How many largest transactions?", 5, 30, 10)

    largest_transactions = (
        purchases_df
        .sort_values("amount", ascending=False)
        .head(top_n)
        [[
            "transaction_date",
            "description",
            "category",
            "amount",
            "source_file"
        ]]
    )

    largest_display = largest_transactions.copy()
    largest_display["transaction_date"] = largest_display["transaction_date"].dt.strftime("%Y-%m-%d")
    largest_display["amount"] = largest_display["amount"].apply(money)

    st.dataframe(largest_display, use_container_width=True)

    st.divider()

    st.subheader("All Transactions")

    search = st.text_input("Search merchant or description")

    filtered_display = purchases_df.copy()

    if search:
        filtered_display = filtered_display[
            filtered_display["description"].str.contains(search, case=False, na=False)
        ]

    filtered_display = filtered_display.sort_values("transaction_date")

    final_display = filtered_display[[
        "transaction_date",
        "posting_date",
        "description",
        "category",
        "amount",
        "source_file"
    ]].copy()

    final_display["transaction_date"] = final_display["transaction_date"].dt.strftime("%Y-%m-%d")
    final_display["posting_date"] = final_display["posting_date"].dt.strftime("%Y-%m-%d")
    final_display["amount"] = final_display["amount"].apply(money)

    st.dataframe(final_display, use_container_width=True)

    csv_export = filtered_display.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download categorized CSV",
        data=csv_export,
        file_name=f"expenses_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv"
    )

    if not credits_df.empty:
        st.divider()
        st.subheader("Refunds / Credits Found")

        credit_display = credits_df[[
            "transaction_date",
            "description",
            "amount",
            "source_file"
        ]].copy()

        credit_display["transaction_date"] = credit_display["transaction_date"].dt.strftime("%Y-%m-%d")
        credit_display["amount"] = credit_display["amount"].apply(money)

        st.dataframe(credit_display, use_container_width=True)

else:
    st.info("Upload your Bank of America PDF statements to start.")
