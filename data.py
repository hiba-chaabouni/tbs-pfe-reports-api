"""In-memory "database": plain Python lists of dictionaries.

Everything here is reset every time the server restarts (no database on purpose).
"""

# ---------------------------------------------------------------------------
# STUDENTS
# student_id is CIN-inspired (8 digits) -> sensitive, never shown on public routes.
# double_major: 0 = single major (max 1 report), 1 = double major (max 2 reports,
# in different majors).
# ---------------------------------------------------------------------------
students = [
    {"student_id": "11165247", "first_name": "Yasmine", "last_name": "Ben Salah",
     "double_major": 0, "level": "senior"},
    {"student_id": "09876543", "first_name": "Mohamed Aziz", "last_name": "Trabelsi",
     "double_major": 1, "level": "senior"},
    # Formally a freshman (failed a first-year course) but already has a PFE.
    {"student_id": "12458796", "first_name": "Eya", "last_name": "Jebali",
     "double_major": 0, "level": "freshman"},
    {"student_id": "07341289", "first_name": "Rayen", "last_name": "Gharbi",
     "double_major": 1, "level": "senior"},
    {"student_id": "13579024", "first_name": "Malek", "last_name": "Mejri",
     "double_major": 0, "level": "senior"},
    # Double major with only 1 report so far -> can still add one in another major.
    {"student_id": "14820367", "first_name": "Nour", "last_name": "Chaabouni",
     "double_major": 1, "level": "junior"},
    {"student_id": "08264519", "first_name": "Youssef", "last_name": "Ayari",
     "double_major": 0, "level": "senior"},
    # No report yet -> useful for a successful POST /reports demo.
    {"student_id": "11937402", "first_name": "Ranim", "last_name": "Hammami",
     "double_major": 0, "level": "sophomore"},
]

# ---------------------------------------------------------------------------
# REPORTS
# report_id format: TBS-PFE-<year>-<major code>-<3-digit sequence>
# student_id is an INTERNAL foreign key -> stripped by public_report() in app.py.
# ---------------------------------------------------------------------------
reports = [
    {
        "report_id": "TBS-PFE-2024-BA-017",
        "student_id": "11165247",
        "major": "BA",
        "title": "Design of a Customer Churn Prediction Model: Case of a Tunisian Telecom Operator",
        "type": "Internship report",
        "key_feature_1": "Machine learning",
        "key_feature_2": "Customer segmentation",
        "key_feature_3": "Python (scikit-learn)",
        "date": "2024-06-20",
    },
    {
        "report_id": "TBS-PFE-2023-FIN-008",
        "student_id": "09876543",
        "major": "FIN",
        "title": "Credit Risk Scoring Using Logistic Regression: Case of a Tunisian Commercial Bank",
        "type": "Internship report",
        "key_feature_1": "Credit scoring",
        "key_feature_2": "Logistic regression",
        "key_feature_3": "Basel III requirements",
        "date": "2023-06-28",
    },
    {
        "report_id": "TBS-PFE-2023-BA-011",
        "student_id": "09876543",
        "major": "BA",
        "title": "Power BI Dashboard for Branch Performance Monitoring: Case of a Tunisian Microfinance Institution",
        "type": "Internship report",
        "key_feature_1": "Power BI dashboard",
        "key_feature_2": "KPI design",
        "key_feature_3": "Data cleaning",
        "date": "2023-07-05",
    },
    {
        "report_id": "TBS-PFE-2025-MKT-004",
        "student_id": "12458796",
        "major": "MKT",
        "title": "Influencer Marketing and Gen-Z Purchase Intention: Case of a Tunisian Cosmetics Brand",
        "type": "Research thesis",
        "key_feature_1": "Influencer marketing",
        "key_feature_2": "Survey analysis",
        "key_feature_3": "Structural equation modeling",
        "date": "2025-06-15",
    },
    {
        "report_id": "TBS-PFE-2022-IT-005",
        "student_id": "07341289",
        "major": "IT",
        "title": "Development of a Web-Based Inventory Management System: Case of a Sfax Olive Oil Exporter",
        "type": "Internship report",
        "key_feature_1": "Flask web application",
        "key_feature_2": "Relational database design",
        "key_feature_3": "Agile Scrum",
        "date": "2022-06-30",
    },
    {
        "report_id": "TBS-PFE-2022-IBE-002",
        "student_id": "07341289",
        "major": "IBE",
        "title": "Impact of the EU-Tunisia Free Trade Agreement on Agri-Food Exports: An Empirical Analysis",
        "type": "Research thesis",
        "key_feature_1": "Gravity model",
        "key_feature_2": "Panel data econometrics",
        "key_feature_3": "Trade policy",
        "date": "2022-07-12",
    },
    {
        "report_id": "TBS-PFE-2021-ACC-009",
        "student_id": "13579024",
        "major": "ACC",
        "title": "Implementation of IFRS 16 Lease Accounting: Case of a Tunisian Retail Group",
        "type": "Internship report",
        "key_feature_1": "IFRS 16",
        "key_feature_2": "Financial statement analysis",
        "key_feature_3": "Audit procedures",
        "date": "2021-06-25",
    },
    {
        "report_id": "TBS-PFE-2025-BA-021",
        "student_id": "14820367",
        "major": "BA",
        "title": "Market Basket Analysis for Cross-Selling Recommendations: Case of a Tunisian Supermarket Chain",
        "type": "Internship report",
        "key_feature_1": "Association rules",
        "key_feature_2": "Recommendation system",
        "key_feature_3": "Python (pandas)",
        "date": "2025-06-18",
    },
    {
        "report_id": "TBS-PFE-2024-FIN-014",
        "student_id": "08264519",
        "major": "FIN",
        "title": "Business Plan for a Mobile Micro-Savings App Targeting Tunisian University Students",
        "type": "Entrepreneurial project",
        "key_feature_1": "Fintech",
        "key_feature_2": "Financial forecasting",
        "key_feature_3": "Business model canvas",
        "date": "2024-06-27",
    },
]
