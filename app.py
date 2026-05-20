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


# -----------------------------
# Language support
# -----------------------------
TRANSLATIONS = {
    "en": {
        "language_label": "Language / اللغة",
        "app_title": "Credit Card Expense Analyzer",
        "app_intro": (
            "Upload one or more credit card PDF statements. "
            "The app filters by transaction date, excludes card payments, "
            "categorizes expenses, and shows monthly totals."
        ),
        "upload_pdf": "Upload PDF statements",
        "year": "Year",
        "month": "Month",
        "subtract_refunds": "Subtract merchant refunds/credits from net total",
        "remove_duplicates": "Remove exact duplicate rows",
        "remove_duplicates_help": "Useful if the same statement is uploaded twice.",
        "no_transactions_found": "No transactions found. Try another PDF or check if the statement text is selectable.",
        "no_month_transactions": "No transactions found for the selected month.",
        "monthly_summary": "Monthly Summary",
        "gross_spending": "Gross Spending",
        "merchant_refunds": "Merchant Credits / Refunds",
        "net_spending": "Net Spending",
        "purchases": "Purchases",
        "gross_help": "Purchases before subtracting merchant refunds.",
        "refund_help": "Money returned by merchants. Card payments are not included.",
        "net_help": "Your real spending after merchant refunds.",
        "purchases_help": "Number of purchase rows found for the selected month.",
        "removed_duplicates": "Removed {count} exact duplicate transaction row(s).",
        "excluded_payment_caption": "Excluded {count} card payment row(s) totaling {amount} from spending and refund calculations.",
        "spending_by_category": "Spending by Category",
        "chart_type": "Chart type",
        "pie": "Pie",
        "bar": "Bar",
        "category_share": "Category Share",
        "category_totals": "Category Totals",
        "category": "Category",
        "amount": "Amount",
        "total": "Total",
        "count": "Count",
        "largest_transactions": "Largest Transactions",
        "top_n": "How many largest transactions?",
        "all_purchases": "All Purchases",
        "search": "Search merchant or description",
        "download_csv": "Download categorized CSV",
        "merchant_refunds_found": "Merchant Refunds / Credits Found",
        "excluded_card_payments": "Excluded card payments",
        "no_card_payments": "No card payments found for this month.",
        "upload_start": "Upload your Bank of America PDF statements to start.",
        "transaction_date": "Transaction Date",
        "posting_date": "Posting Date",
        "description": "Description",
        "source_file": "Source File",
        "account_number": "Account Number",
        "summary_note": "Net Spending is the number that best represents your real monthly expenses.",
    },
    "ar": {
        "language_label": "اللغة / Language",
        "app_title": "محلل مصاريف البطاقة الائتمانية",
        "app_intro": (
            "ارفع كشف بطاقة ائتمانية واحد أو أكثر بصيغة PDF. "
            "التطبيق يفلتر العمليات حسب تاريخ العملية، يستبعد مدفوعات البطاقة، "
            "يصنف المصاريف، ويعرض ملخص الشهر."
        ),
        "upload_pdf": "ارفع كشوفات البطاقة بصيغة PDF",
        "year": "السنة",
        "month": "الشهر",
        "subtract_refunds": "اطرح المبالغ المسترجعة من صافي المصاريف",
        "remove_duplicates": "حذف العمليات المكررة",
        "remove_duplicates_help": "مفيد إذا رفعت نفس الكشف أكثر من مرة.",
        "no_transactions_found": "لم يتم العثور على عمليات. جرب ملف PDF آخر أو تأكد أن نص الكشف قابل للقراءة.",
        "no_month_transactions": "لم يتم العثور على عمليات للشهر المحدد.",
        "monthly_summary": "ملخص الشهر",
        "gross_spending": "إجمالي المشتريات",
        "merchant_refunds": "المبالغ المسترجعة من المتاجر",
        "net_spending": "صافي المصاريف",
        "purchases": "عدد عمليات الشراء",
        "gross_help": "كل المشتريات قبل طرح المبالغ المسترجعة.",
        "refund_help": "مبالغ رجعت لك من المتاجر. مدفوعات البطاقة لا تدخل هنا.",
        "net_help": "المبلغ الحقيقي الذي صرفته بعد خصم المبالغ المسترجعة.",
        "purchases_help": "عدد عمليات الشراء الموجودة في الشهر المحدد.",
        "removed_duplicates": "تم حذف {count} عملية مكررة.",
        "excluded_payment_caption": "تم استبعاد {count} مدفوعات بطاقة بإجمالي {amount} من حساب المصاريف والمبالغ المسترجعة.",
        "spending_by_category": "المصاريف حسب التصنيف",
        "chart_type": "نوع الرسم",
        "pie": "دائري",
        "bar": "أعمدة",
        "category_share": "نسبة كل تصنيف",
        "category_totals": "إجمالي التصنيفات",
        "category": "التصنيف",
        "amount": "المبلغ",
        "total": "الإجمالي",
        "count": "العدد",
        "largest_transactions": "أكبر العمليات",
        "top_n": "كم عملية تريد عرضها؟",
        "all_purchases": "كل المشتريات",
        "search": "ابحث باسم المتجر أو الوصف",
        "download_csv": "تحميل الملف بعد التصنيف CSV",
        "merchant_refunds_found": "المبالغ المسترجعة من المتاجر",
        "excluded_card_payments": "مدفوعات البطاقة المستبعدة",
        "no_card_payments": "لا توجد مدفوعات بطاقة لهذا الشهر.",
        "upload_start": "ارفع كشوفات Bank of America بصيغة PDF للبدء.",
        "transaction_date": "تاريخ العملية",
        "posting_date": "تاريخ التسجيل",
        "description": "الوصف",
        "source_file": "الملف المصدر",
        "account_number": "رقم الحساب",
        "summary_note": "صافي المصاريف هو الرقم الأهم لأنه يمثل مصاريفك الحقيقية للشهر.",
    },
}

CATEGORY_LABELS_AR = {
    "Groceries": "بقالة وتموين",
    "Restaurants / Coffee": "مطاعم وقهوة",
    "Gas / Parking / Transportation": "بنزين ومواقف ومواصلات",
    "Insurance": "تأمين",
    "Online Shopping": "تسوق إلكتروني",
    "Online Subscriptions": "اشتراكات إلكترونية",
    "Shopping": "تسوق",
    "Home / Tools": "منزل وأدوات",
    "Medical / Health": "طبي وصحي",
    "Travel / Entertainment": "سفر وترفيه",
    "Business / Services": "خدمات وأعمال",
    "Laundry": "غسيل ملابس",
    "Other / Unknown": "أخرى / غير معروف",
}

MONTH_NAMES_AR = {
    1: "يناير",
    2: "فبراير",
    3: "مارس",
    4: "أبريل",
    5: "مايو",
    6: "يونيو",
    7: "يوليو",
    8: "أغسطس",
    9: "سبتمبر",
    10: "أكتوبر",
    11: "نوفمبر",
    12: "ديسمبر",
}


def t(key: str) -> str:
    return TRANSLATIONS[st.session_state.get("lang", "en")].get(key, key)


def localize_category(category: str) -> str:
    if st.session_state.get("lang") == "ar":
        return CATEGORY_LABELS_AR.get(category, category)
    return category


def localize_month(month_num: int) -> str:
    if st.session_state.get("lang") == "ar":
        return MONTH_NAMES_AR[month_num]
    return datetime(2000, month_num, 1).strftime("%B")


# Language switch at the top
left, right = st.columns([5, 1.6])
with right:
    selected_language = st.radio(
        "Language / اللغة",
        options=["EN", "AR"],
        horizontal=True,
        label_visibility="collapsed",
    )

st.session_state["lang"] = "ar" if selected_language == "AR" else "en"
IS_AR = st.session_state["lang"] == "ar"

if IS_AR:
    st.markdown(
        """
        <style>
        .stApp { direction: rtl; text-align: right; }
        .stDataFrame, .stTable, .stPlotlyChart { direction: ltr; text-align: left; }
        div[data-testid="stMetric"] { direction: rtl; text-align: right; }
        input, textarea { direction: rtl; text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .stApp { direction: ltr; text-align: left; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Categorization and parsing
# -----------------------------
CATEGORY_RULES = {
    # Specific online merchants come before generic merchants like COSTCO.
    "Online Shopping": [
        "WWW COSTCO COM", "BESTBUYCOM", "EBAY", "PAYPAL *EBAY",
        "AMZ", "AMAZON", "QINK", "TRYAURELA", "TEMU", "SHEIN"
    ],
    "Online Subscriptions": [
        "OPENAI", "CHATGPT", "CLAUDE", "GOOGLE WORKSPACE",
        "GOOGLE MOODLOG", "APPLE.COM", "RING", "OPUS CLIP",
        "NAME-CHEAP", "NAMECHEAP", "HONEYTOON", "USP*COMIC",
        "NETFLIX", "HULU", "SPOTIFY", "YOUTUBE"
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
        "PROGRESSIVE", "AETNA", "STATE FARM", "GEICO", "LIBERTY MUTUAL", "ALLSTATE", "CIGNA"
    ],
    "Medical / Health": [
        "DH EPIC", "HOSP", "CLINIC", "CVS", "PHARMACY"
    ],
    "Shopping": [
        "ROSS", "TARGET", "DOLLARTREE", "DOLLAR TREE", "FIVE BELOW",
        "WALGREENS", "MARSHALLS", "TJ MAXX"
    ],
    "Home / Tools": [
        "ACE", "TAMARAC SQUARE ACE", "MEGA HOME", "HOME DEPOT", "LOWES"
    ],
    "Travel / Entertainment": [
        "GREAT WOLF", "LODGE", "HOTEL", "AIRBNB", "EXPEDIA", "BOOKING.COM"
    ],
    "Business / Services": [
        "USPS", "POST OFFICE", "UPS", "FEDEX"
    ],
    "Laundry": [
        "LAVANDERIA", "LAUNDRY"
    ],
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


def prepare_display_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    display_df = df[columns].copy()

    for col in ["transaction_date", "posting_date"]:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col]).dt.strftime("%Y-%m-%d")

    if "amount" in display_df.columns:
        display_df["amount"] = display_df["amount"].apply(money)

    if "category" in display_df.columns:
        display_df["category"] = display_df["category"].apply(localize_category)

    rename_map = {
        "transaction_date": t("transaction_date"),
        "posting_date": t("posting_date"),
        "description": t("description"),
        "category": t("category"),
        "amount": t("amount"),
        "source_file": t("source_file"),
        "account_number": t("account_number"),
        "total": t("total"),
        "count": t("count"),
    }
    return display_df.rename(columns=rename_map)


# -----------------------------
# UI
# -----------------------------
st.title(t("app_title"))
st.write(t("app_intro"))

uploaded_files = st.file_uploader(
    t("upload_pdf"),
    type=["pdf"],
    accept_multiple_files=True
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_year = st.number_input(
        t("year"),
        min_value=2020,
        max_value=2035,
        value=2026,
        step=1
    )

with col2:
    selected_month = st.selectbox(
        t("month"),
        options=list(range(1, 13)),
        index=3,
        format_func=localize_month,
    )

with col3:
    include_credits = st.checkbox(
        t("subtract_refunds"),
        value=True
    )

with col4:
    remove_duplicates = st.checkbox(
        t("remove_duplicates"),
        value=True,
        help=t("remove_duplicates_help")
    )

if uploaded_files:
    all_transactions = []

    for uploaded_file in uploaded_files:
        text = extract_pdf_text(uploaded_file)
        df = parse_transactions(text, source_file=uploaded_file.name)

        if not df.empty:
            all_transactions.append(df)

    if not all_transactions:
        st.error(t("no_transactions_found"))
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
        st.warning(t("no_month_transactions"))
        st.stop()

    df_month["is_card_payment"] = df_month["description"].apply(is_card_payment)
    df_month["is_refund_or_credit"] = df_month.apply(
        lambda row: is_refund_or_credit(row["description"], row["amount"]),
        axis=1
    )

    analysis_df = df_month[~df_month["is_card_payment"]].copy()

    purchases_df = analysis_df[analysis_df["amount"] > 0].copy()
    purchases_df["category"] = purchases_df["description"].apply(categorize_transaction)

    credits_df = analysis_df[analysis_df["is_refund_or_credit"]].copy()
    credits_total = credits_df["amount"].sum()

    card_payments_df = df_month[df_month["is_card_payment"]].copy()
    card_payments_total = card_payments_df["amount"].sum()

    gross_spending = purchases_df["amount"].sum()
    net_spending = gross_spending + credits_total if include_credits else gross_spending

    st.subheader(t("monthly_summary"))
    st.caption(t("summary_note"))

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(t("gross_spending"), money(gross_spending), help=t("gross_help"))
    metric2.metric(t("merchant_refunds"), money(credits_total), help=t("refund_help"))
    metric3.metric(t("net_spending"), money(net_spending), help=t("net_help"))
    metric4.metric(t("purchases"), len(purchases_df), help=t("purchases_help"))

    if removed_count > 0:
        st.info(t("removed_duplicates").format(count=removed_count))

    if not card_payments_df.empty:
        st.caption(
            t("excluded_payment_caption").format(
                count=len(card_payments_df),
                amount=money(card_payments_total)
            )
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
    category_summary["category_label"] = category_summary["category"].apply(localize_category)

    st.subheader(t("spending_by_category"))

    col_chart, col_table = st.columns([1.2, 1])

    with col_chart:
        chart_options = [t("pie"), t("bar")]
        chart_type = st.radio(t("chart_type"), chart_options, horizontal=True)

        if chart_type == t("pie"):
            fig = px.pie(
                category_summary,
                names="category_label",
                values="total",
                title=t("category_share")
            )
        else:
            fig = px.bar(
                category_summary,
                x="category_label",
                y="total",
                title=t("category_totals")
            )
            fig.update_layout(xaxis_title=t("category"), yaxis_title=t("amount"))

        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        display_summary = category_summary[["category", "total", "count"]].copy()
        display_summary["category"] = display_summary["category"].apply(localize_category)
        display_summary["total"] = display_summary["total"].apply(money)
        display_summary = display_summary.rename(columns={
            "category": t("category"),
            "total": t("total"),
            "count": t("count"),
        })
        st.dataframe(display_summary, use_container_width=True)

    st.divider()

    st.subheader(t("largest_transactions"))

    top_n = st.slider(t("top_n"), 5, 30, 10)

    largest_transactions = (
        purchases_df
        .sort_values("amount", ascending=False)
        .head(top_n)
    )

    largest_display = prepare_display_df(
        largest_transactions,
        [
            "transaction_date",
            "description",
            "category",
            "amount",
            "source_file",
            "account_number",
        ]
    )

    st.dataframe(largest_display, use_container_width=True)

    st.divider()

    st.subheader(t("all_purchases"))

    search = st.text_input(t("search"))

    filtered_display = purchases_df.copy()

    if search:
        filtered_display = filtered_display[
            filtered_display["description"].str.contains(search, case=False, na=False)
        ]

    filtered_display = filtered_display.sort_values("transaction_date")

    final_display = prepare_display_df(
        filtered_display,
        [
            "transaction_date",
            "posting_date",
            "description",
            "category",
            "amount",
            "source_file",
            "account_number",
        ]
    )

    st.dataframe(final_display, use_container_width=True)

    csv_export = filtered_display.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label=t("download_csv"),
        data=csv_export,
        file_name=f"expenses_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv"
    )

    if not credits_df.empty:
        st.divider()
        st.subheader(t("merchant_refunds_found"))

        credit_display = prepare_display_df(
            credits_df,
            [
                "transaction_date",
                "description",
                "amount",
                "source_file",
                "account_number",
            ]
        )

        st.dataframe(credit_display, use_container_width=True)

    with st.expander(t("excluded_card_payments")):
        if card_payments_df.empty:
            st.write(t("no_card_payments"))
        else:
            payment_display = prepare_display_df(
                card_payments_df,
                [
                    "transaction_date",
                    "description",
                    "amount",
                    "source_file",
                    "account_number",
                ]
            )
            st.dataframe(payment_display, use_container_width=True)

else:
    st.info(t("upload_start"))
