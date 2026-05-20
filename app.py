import re
from datetime import datetime, date

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
    "Online Subscriptions": [
        "OPENAI", "CHATGPT", "CLAUDE", "GOOGLE WORKSPACE",
        "GOOGLE MOODLOG", "APPLE.COM", "RING", "OPUS CLIP",
        "NAME-CHEAP", "NAMECHEAP", "HONEYTOON", "USP*COMIC"
    ],
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
        "PROGRESSIVE", "Aetna", "State Farm", "GEICO", "Liberty Mutual", "Allstate","Cigna"
    ],
    "Online Subscriptions": [
        "OPENAI", "CHATGPT", "CLAUDE", "GOOGLE WORKSPACE",
        "GOOGLE MOODLOG", "APPLE.COM", "RING", "OPUS CLIP",
        "NAME-CHEAP", "NAMECHEAP", "HONEYTOON", "USP*COMIC"
    ],
    "Medical / Health": [
        "DH EPIC", "HOSP", "CLINIC"
    ],
    "Shopping": [
        "ROSS", "TARGET", "DOLLARTREE", "DOLLAR TREE", "FIVE BELOW",
        "WALGREENS"
    ],
    "Home / Tools": [
        "ACE", "TAMARAC SQUARE ACE", "MEGA HOME"
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


CARD_PAYMENT_KEYWORDS = [
    "PAYMENT FROM CHK",
    "ONLINE/MOBILE RECURRING FROM CHK",
    "MOBILE PAYMENT",
    "ONLINE PAYMENT",
    "AUTOPAY",
    "AUTO PAYMENT",
    "THANK YOU",
    "PAYMENT - THANK YOU",
    "PAYMENT THANK YOU",
    "PAYMENT RECEIVED",
    "BANK OF AMERICA PAYMENT",
    "BOFA PAYMENT",
]

TRANSACTION_COLUMNS = [
    "transaction_date_raw",
    "posting_date_raw",
    "description",
    "amount",
    "source_file",
    "account_number",
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


def extract_account_number(text: str) -> str:
    """Returns the account number if it appears in the statement text."""
    match = re.search(r"Account#\s*([\d\s]+)", text)
    if not match:
        match = re.search(r"Account Number:\s*([\d\s]+)", text)

    if not match:
        return "Unknown"

    return re.sub(r"\s+", " ", match.group(1)).strip()


def parse_transactions(text: str, source_file: str = "") -> pd.DataFrame:
    """
    Extract transaction rows from Bank of America PDF text.

    Expected row shape:
    MM/DD MM/DD DESCRIPTION ... AMOUNT

    The first date is the transaction date.
    The second date is the posting date.
    """
    transactions = []
    account_number = extract_account_number(text)

    # Some statement rows wrap to the next line, so we parse line by line and
    # ignore continuation-only lines. This is reliable for the BofA text layout.
    for raw_line in text.splitlines():
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
            "amount": amount,
            "source_file": source_file,
            "account_number": account_number,
        })

    if not transactions:
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)

    return pd.DataFrame(transactions)


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


def is_card_payment(description: str) -> bool:
    """True for credit card payments. These are not expenses or refunds."""
    desc = description.upper()

    if any(keyword in desc for keyword in CARD_PAYMENT_KEYWORDS):
        return True

    # Catch generic payment rows, but avoid merchant names like PayPal.
    if "PAYMENT" in desc and "PAYPAL" not in desc:
        return True

    return False


def is_refund_or_credit(description: str, amount: float) -> bool:
    """True for merchant credits/refunds, not card payments."""
    return amount < 0 and not is_card_payment(description)


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


def format_money_column(df: pd.DataFrame, column: str = "amount") -> pd.DataFrame:
    display_df = df.copy()
    display_df[column] = display_df[column].apply(money)
    return display_df


st.title("Credit Card Expense Analyzer")

st.write(
    "Upload one or more credit card PDF statements. "
    "The app filters by transaction date, excludes card payments, "
    "categorizes expenses, and shows monthly totals."
)

uploaded_files = st.file_uploader(
    "Upload PDF statements",
    type=["pdf"],
    accept_multiple_files=True
)

col1, col2, col3, col4 = st.columns(4)

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
        "Subtract merchant refunds/credits from net total",
        value=True
    )

with col4:
    remove_duplicates = st.checkbox(
        "Remove exact duplicate rows",
        value=True,
        help="Useful if the same statement is uploaded twice."
    )

if uploaded_files:
    all_transactions = []

    for uploaded_file in uploaded_files:
        text = extract_pdf_text(uploaded_file)
        df = parse_transactions(text, source_file=uploaded_file.name)

        if not df.empty:
            all_transactions.append(df)

    if not all_transactions:
        st.error("No transactions found. Try another PDF or check if the statement text is selectable.")
        st.stop()

    df_all = pd.concat(all_transactions, ignore_index=True)
    df_all = attach_year(df_all, selected_year)

    if remove_duplicates:
        before_count = len(df_all)
        df_all = df_all.drop_duplicates(
            subset=[
                "account_number",
                "transaction_date_raw",
                "posting_date_raw",
                "description",
                "amount",
            ],
            keep="first"
        ).copy()
        removed_count = before_count - len(df_all)
    else:
        removed_count = 0

    df_month = filter_by_month(df_all, selected_year, selected_month)

    if df_month.empty:
        st.warning("No transactions found for the selected month.")
        st.stop()

    df_month["is_card_payment"] = df_month["description"].apply(is_card_payment)
    df_month["is_refund_or_credit"] = df_month.apply(
        lambda row: is_refund_or_credit(row["description"], row["amount"]),
        axis=1
    )

    # Remove card payments before calculating expenses or refunds.
    analysis_df = df_month[~df_month["is_card_payment"]].copy()

    purchases_df = analysis_df[analysis_df["amount"] > 0].copy()
    purchases_df["category"] = purchases_df["description"].apply(categorize_transaction)

    credits_df = analysis_df[analysis_df["is_refund_or_credit"]].copy()
    credits_total = credits_df["amount"].sum()

    card_payments_df = df_month[df_month["is_card_payment"]].copy()
    card_payments_total = card_payments_df["amount"].sum()

    gross_spending = purchases_df["amount"].sum()
    net_spending = gross_spending + credits_total if include_credits else gross_spending

    st.subheader("Monthly Summary")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Gross Spending", money(gross_spending))
    metric2.metric("Merchant Credits / Refunds", money(credits_total))
    metric3.metric("Net Spending", money(net_spending))
    metric4.metric("Purchases", len(purchases_df))

    if removed_count > 0:
        st.info(f"Removed {removed_count} exact duplicate transaction row(s).")

    if not card_payments_df.empty:
        st.caption(
            f"Excluded {len(card_payments_df)} card payment row(s) totaling "
            f"{money(card_payments_total)} from spending and refund calculations."
        )

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
        chart_type = st.radio("Chart type", ["Pie", "Bar"], horizontal=True)

        if chart_type == "Pie":
            fig = px.pie(
                category_summary,
                names="category",
                values="total",
                title="Category Share"
            )
        else:
            fig = px.bar(
                category_summary,
                x="category",
                y="total",
                title="Category Totals"
            )
            fig.update_layout(xaxis_title="Category", yaxis_title="Amount")

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
            "source_file",
            "account_number",
        ]]
    )

    largest_display = largest_transactions.copy()
    largest_display["transaction_date"] = largest_display["transaction_date"].dt.strftime("%Y-%m-%d")
    largest_display["amount"] = largest_display["amount"].apply(money)

    st.dataframe(largest_display, use_container_width=True)

    st.divider()

    st.subheader("All Purchases")

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
        "source_file",
        "account_number",
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
        st.subheader("Merchant Refunds / Credits Found")

        credit_display = credits_df[[
            "transaction_date",
            "description",
            "amount",
            "source_file",
            "account_number",
        ]].copy()

        credit_display["transaction_date"] = credit_display["transaction_date"].dt.strftime("%Y-%m-%d")
        credit_display["amount"] = credit_display["amount"].apply(money)

        st.dataframe(credit_display, use_container_width=True)

    with st.expander("Excluded card payments"):
        if card_payments_df.empty:
            st.write("No card payments found for this month.")
        else:
            payment_display = card_payments_df[[
                "transaction_date",
                "description",
                "amount",
                "source_file",
                "account_number",
            ]].copy()
            payment_display["transaction_date"] = payment_display["transaction_date"].dt.strftime("%Y-%m-%d")
            payment_display["amount"] = payment_display["amount"].apply(money)
            st.dataframe(payment_display, use_container_width=True)

else:
    st.info("Upload your Bank of America PDF statements to start.")
