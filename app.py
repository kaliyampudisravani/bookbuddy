import os
import re
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# =========================================================
# BOOKBUDDY - COMPLETE STREAMLIT APP
# =========================================================

st.set_page_config(page_title="BookBuddy", page_icon="📚", layout="wide")

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Streamlit Cloud credentials (local .env remains supported)
try:
    SUPABASE_URL = SUPABASE_URL or st.secrets["SUPABASE_URL"]
except Exception:
    pass
try:
    SUPABASE_KEY = SUPABASE_KEY or st.secrets["SUPABASE_KEY"]
except Exception:
    pass

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Configuration error: SUPABASE_URL or SUPABASE_KEY is missing.")
    st.info("Add both values to the .env file in the same folder as app.py.")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:
    st.error("Could not connect to Supabase. Check your URL and key.")
    st.caption(str(exc))
    st.stop()

# ------------------------- CONSTANTS -------------------------

BOOK_CATEGORIES = ["Novels", "General Books", "Semester Textbooks"]
NOVEL_TYPES = [
    "Romance", "Thriller", "Mystery", "Fantasy",
    "Horror", "Science Fiction", "Historical Fiction", "Other"
]
GENERAL_BOOK_TYPES = [
    "Story Books", "Self-Help", "Competitive Exam Books",
    "Reference Books", "Biography", "Other"
]
BOOK_CONDITIONS = ["New", "Like New", "Good", "Acceptable"]
LISTING_TYPES = ["Sell", "Exchange", "Free"]
ORDER_STATUSES = ["Placed", "Accepted", "Packed", "Shipped", "Delivered"]

# ------------------------- SESSION -------------------------

SESSION_DEFAULTS = {
    "logged_in": False,
    "student_user_id": None,
    "access_token": None,
    "refresh_token": None,
    "student_email": ""
}
for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.logged_in and st.session_state.access_token and st.session_state.refresh_token:
    try:
        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )
    except Exception:
        for key, value in SESSION_DEFAULTS.items():
            st.session_state[key] = value
        st.warning("Your session expired. Please log in again.")

# ------------------------- HELPERS -------------------------

def valid_email(email):
    return re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        email.strip()
    ) is not None

def show_error(message, exc):
    st.error(message)
    st.caption(str(exc))

def get_colleges():
    return (
        supabase.table("colleges")
        .select("id, college_name")
        .order("college_name")
        .execute().data or []
    )

def get_student_profile(user_id):
    rows = (
        supabase.table("students")
        .select("id, full_name, college_id, course, semester, phone")
        .eq("id", user_id)
        .limit(1)
        .execute().data or []
    )
    return rows[0] if rows else None

def save_student_profile(user_id, full_name, college_id, course, semester, phone):
    data = {
        "id": user_id,
        "full_name": full_name.strip(),
        "college_id": int(college_id),
        "course": course.strip(),
        "semester": int(semester),
        "phone": phone.strip() or None
    }
    return supabase.table("students").upsert(data).execute()

def get_book(book_id):
    rows = (
        supabase.table("books")
        .select("id, seller_id, title, author, status, listing_type, price")
        .eq("id", book_id)
        .limit(1)
        .execute().data or []
    )
    return rows[0] if rows else None

def display_price(book):
    if book.get("listing_type") == "Free":
        return "Free"
    if book.get("listing_type") == "Exchange":
        return "Exchange"
    return f"₹{book.get('price') or 0}"

def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ------------------------- HEADER -------------------------

st.title("📚 BookBuddy")
st.caption("Exchange • Sell • Give Away")
st.divider()

# =========================================================
# LOGIN / REGISTRATION
# =========================================================

if not st.session_state.logged_in:
    st.subheader("Welcome to BookBuddy!")
    login_tab, register_tab, reset_tab = st.tabs(["Login", "Register", "Forgot Password?"])

    with login_tab:
        st.subheader("Student Login")
        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            login_clicked = st.form_submit_button("Login", use_container_width=True)

        if login_clicked:
            if not email.strip() or not password:
                st.warning("Please enter both your email address and password.")
            elif not valid_email(email):
                st.warning("Please enter a valid email address.")
            else:
                try:
                    result = supabase.auth.sign_in_with_password({
                        "email": email.strip(),
                        "password": password
                    })
                    if result.user and result.session:
                        st.session_state.logged_in = True
                        st.session_state.student_user_id = result.user.id
                        st.session_state.access_token = result.session.access_token
                        st.session_state.refresh_token = result.session.refresh_token
                        st.session_state.student_email = result.user.email or email.strip()
                        st.success("Login successful. Welcome to BookBuddy!")
                        st.rerun()
                    else:
                        st.error("Login was not completed. Please try again.")
                except Exception as exc:
                    show_error("Login failed. Check your email and password.", exc)

    with register_tab:
        st.subheader("Create Student Account")
        try:
            colleges = get_colleges()
        except Exception as exc:
            colleges = []
            show_error("Could not load the college list.", exc)

        if not colleges:
            st.info("No colleges are available. Please ask the project administrator to add colleges.")
        else:
            college_names = [item["college_name"] for item in colleges]
            college_ids = [item["id"] for item in colleges]

            with st.form("register_form"):
                full_name = st.text_input("Full name")
                reg_email = st.text_input("Email address")
                reg_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                selected_college = st.selectbox("College", college_names)
                course = st.text_input("Course", value="B.Sc Data Science")
                semester = st.selectbox("Semester", [1, 2, 3, 4, 5, 6, 7, 8])
                phone = st.text_input("Phone number (optional)")
                register_clicked = st.form_submit_button("Register", use_container_width=True)

            if register_clicked:
                if not full_name.strip():
                    st.warning("Please enter your full name.")
                elif not valid_email(reg_email):
                    st.warning("Please enter a valid email address.")
                elif len(reg_password) < 6:
                    st.warning("Password must contain at least 6 characters.")
                elif reg_password != confirm_password:
                    st.warning("The passwords do not match.")
                elif phone.strip() and (not phone.strip().isdigit() or len(phone.strip()) != 10):
                    st.warning("Enter a valid 10-digit phone number, or leave it blank.")
                else:
                    try:
                        college_id = college_ids[college_names.index(selected_college)]
                        result = supabase.auth.sign_up({
                            "email": reg_email.strip(),
                            "password": reg_password,
                            "options": {
                                "data": {
                                    "full_name": full_name.strip(),
                                    "college_id": college_id,
                                    "course": course.strip(),
                                    "semester": semester,
                                    "phone": phone.strip() or None
                                }
                            }
                        })
                        if result.user and result.session:
                            save_student_profile(
                                result.user.id, full_name, college_id,
                                course, semester, phone
                            )
                            st.success("Registration successful. You can now log in.")
                        elif result.user:
                            st.success(
                                "Account created. Check your email for the verification link, "
                                "then return here and log in."
                            )
                        else:
                            st.error("Registration was not completed. Please try again.")
                    except Exception as exc:
                        show_error("Registration failed. Check the form and Supabase settings.", exc)

    with reset_tab:
        st.subheader("Reset your password")
        st.write("Enter your registered email address. Supabase will send a password-reset link.")
        with st.form("forgot_password_form"):
            reset_email = st.text_input("Registered email address", key="reset_email")
            reset_clicked = st.form_submit_button("Send reset link", use_container_width=True)
        if reset_clicked:
            if not valid_email(reset_email):
                st.warning("Please enter a valid email address.")
            else:
                try:
                    # Configure the app URL in Supabase Authentication → URL Configuration → Redirect URLs.
                    redirect_url = os.getenv("PASSWORD_RESET_REDIRECT_URL", "")
                    options = {"redirect_to": redirect_url} if redirect_url else None
                    if options:
                        supabase.auth.reset_password_for_email(reset_email.strip(), options=options)
                    else:
                        supabase.auth.reset_password_for_email(reset_email.strip())
                    st.success("If this email is registered, Supabase will send a password-reset email. Check your inbox and spam folder.")
                    st.info("The reset link must redirect to a page that can complete Supabase password recovery. Add your deployed BookBuddy URL to Supabase Authentication → URL Configuration → Redirect URLs.")
                except Exception as exc:
                    show_error("Could not send the password-reset email. Check Supabase Auth email settings and rate limits.", exc)

# =========================================================
# MAIN APPLICATION
# =========================================================

else:
    user_id = st.session_state.student_user_id
    st.sidebar.success(f"Logged in: {st.session_state.student_email}")
    page = st.sidebar.radio(
        "Menu",
        [
            "My Profile", "Browse Books", "My Wishlist", "Add a Book",
            "Need a Book", "Delivery Address", "My Orders", "Exchange Requests", "Logout"
        ]
    )

    # ------------------------- PROFILE -------------------------

    if page == "My Profile":
        st.subheader("👤 My Student Profile")
        try:
            profile = get_student_profile(user_id)
            colleges = get_colleges()
            if not colleges:
                st.error("No colleges are configured in the database.")
            else:
                names = [c["college_name"] for c in colleges]
                ids = [c["id"] for c in colleges]

                if profile:
                    current_college_id = profile.get("college_id")
                    default_index = ids.index(current_college_id) if current_college_id in ids else 0
                    st.markdown("### Student Details")
                    st.write(f"**Name:** {profile.get('full_name') or 'Not added'}")
                    st.write(f"**Email:** {st.session_state.student_email}")
                    st.write(f"**College:** {names[ids.index(current_college_id)] if current_college_id in ids else 'Not selected'}")
                    st.write(f"**Course:** {profile.get('course') or 'Not added'}")
                    st.write(f"**Semester:** {profile.get('semester') or 'Not added'}")
                    st.write(f"**Phone:** {profile.get('phone') or 'Not added'}")
                    st.divider()
                    st.markdown("### Edit Profile")
                else:
                    st.info("Your student profile is not complete. Please fill in the details below.")
                    default_index = 0

                with st.form("profile_form"):
                    name_value = profile.get("full_name", "") if profile else ""
                    course_value = profile.get("course", "B.Sc Data Science") if profile else "B.Sc Data Science"
                    phone_value = profile.get("phone", "") if profile else ""
                    form_name = st.text_input("Full name", value=name_value)
                    form_college = st.selectbox("College", names, index=default_index)
                    form_course = st.text_input("Course", value=course_value or "")
                    form_semester = st.selectbox(
                        "Semester", [1, 2, 3, 4, 5, 6, 7, 8],
                        index=max(0, min(7, int(profile.get("semester") or 1) - 1)) if profile else 0
                    )
                    form_phone = st.text_input("Phone number (optional)", value=phone_value or "")
                    save_profile_clicked = st.form_submit_button("Save Profile", use_container_width=True)

                if save_profile_clicked:
                    if not form_name.strip() or not form_course.strip():
                        st.warning("Please enter your name and course.")
                    elif form_phone.strip() and (not form_phone.strip().isdigit() or len(form_phone.strip()) != 10):
                        st.warning("Enter a valid 10-digit phone number, or leave it blank.")
                    else:
                        try:
                            save_student_profile(
                                user_id, form_name, ids[names.index(form_college)],
                                form_course, form_semester, form_phone
                            )
                            st.success("Your profile was saved successfully.")
                            st.rerun()
                        except Exception as exc:
                            show_error("Could not save your profile.", exc)
        except Exception as exc:
            show_error("Could not load your profile.", exc)

    # ------------------------- BROWSE BOOKS -------------------------

    elif page == "Browse Books":
        st.subheader("📖 Browse Books")
        try:
            books = (
                supabase.table("books")
                .select(
                    "id, seller_id, title, author, subject, course, semester, "
                    "book_category, book_condition, listing_type, price, description, created_at"
                )
                .eq("status", "Available")
                .order("created_at", desc=True)
                .execute().data or []
            )
            wishlist_rows = (
                supabase.table("wishlist").select("book_id")
                .eq("student_id", user_id).execute().data or []
            )
            wishlist_ids = {row["book_id"] for row in wishlist_rows}
            browse_addresses = (
                supabase.table("delivery_addresses").select(
                    "id, full_name, city, pincode"
                ).eq("student_id", user_id).execute().data or []
            )
            category = st.selectbox("Filter by category", ["All Categories"] + BOOK_CATEGORIES)
            if category != "All Categories":
                books = [b for b in books if b.get("book_category") == category]

            if not books:
                st.info("No available books match this filter.")
            for book in books:
                bid = book["id"]
                with st.container(border=True):
                    st.markdown(f"### 📘 {book.get('title') or 'Untitled'}")
                    st.write(f"**Author:** {book.get('author') or 'Not specified'}")
                    st.write(f"**Category:** {book.get('book_category') or 'Not specified'}")
                    st.write(f"**Subject / Type:** {book.get('subject') or 'Not specified'}")
                    if book.get("book_category") == "Semester Textbooks":
                        st.write(f"**Course:** {book.get('course') or 'Not specified'}")
                        st.write(f"**Semester:** {book.get('semester') or 'Not specified'}")
                    st.write(f"**Condition:** {book.get('book_condition') or 'Not specified'}")
                    st.write(f"**Listing:** {book.get('listing_type') or 'Not specified'}")
                    st.write(f"**Price:** {display_price(book)}")
                    if book.get("description"):
                        st.write(book["description"])

                    # Buyers can place an order directly from the book listing.
                    if book.get("seller_id") != user_id and book.get("listing_type") in ["Sell", "Free"]:
                        if not browse_addresses:
                            st.info("Add a delivery address in the Delivery Address page to order this book.")
                        else:
                            address_options = {
                                f"{a.get('full_name')} — {a.get('city')} — PIN {a.get('pincode')} (ID: {a['id']})": a
                                for a in browse_addresses
                            }
                            with st.form(f"browse_order_form_{bid}"):
                                selected_address_label = st.selectbox(
                                    "Delivery address", list(address_options.keys()), key=f"browse_order_address_{bid}"
                                )
                                confirmed = st.checkbox(
                                    "I confirm this order", key=f"browse_order_confirm_{bid}"
                                )
                                order_now = st.form_submit_button("🛒 Place Order", use_container_width=True)
                            if order_now:
                                if not confirmed:
                                    st.warning("Please confirm before placing the order.")
                                else:
                                    try:
                                        latest = get_book(bid)
                                        if not latest or latest.get("status") != "Available" or latest.get("seller_id") == user_id:
                                            st.error("This book is no longer available. Refresh and try another book.")
                                        else:
                                            supabase.table("orders").insert({
                                                "book_id": latest["id"],
                                                "buyer_id": user_id,
                                                "seller_id": latest["seller_id"],
                                                "address_id": address_options[selected_address_label]["id"],
                                                "price": 0 if latest.get("listing_type") == "Free" else (latest.get("price") or 0),
                                                "status": "Placed"
                                            }).execute()
                                            st.success("Your order was placed successfully. Check My Orders for updates.")
                                            st.rerun()
                                    except Exception as exc:
                                        show_error("Could not place this order. Check the orders table permissions and try again.", exc)

                    if bid in wishlist_ids:
                        if st.button("💔 Remove from Wishlist", key=f"browse_remove_{bid}"):
                            try:
                                supabase.table("wishlist").delete().eq("student_id", user_id).eq("book_id", bid).execute()
                                st.success("Book removed from your wishlist.")
                                st.rerun()
                            except Exception as exc:
                                show_error("Could not remove this book from your wishlist.", exc)
                    else:
                        if st.button("❤️ Add to Wishlist", key=f"browse_add_{bid}"):
                            try:
                                supabase.table("wishlist").insert({"student_id": user_id, "book_id": bid}).execute()
                                st.success("Book added to your wishlist.")
                                st.rerun()
                            except Exception as exc:
                                show_error("Could not add this book. It may already be in your wishlist.", exc)

                    if book.get("seller_id") == user_id:
                        if st.button("🗑️ Delete My Book", key=f"delete_book_{bid}"):
                            try:
                                supabase.table("books").delete().eq("id", bid).eq("seller_id", user_id).execute()
                                st.success("Your book listing was deleted.")
                                st.rerun()
                            except Exception as exc:
                                show_error("Could not delete this book listing.", exc)

                    with st.expander("💬 Comments"):
                        try:
                            comments = (
                                supabase.table("book_comments")
                                .select("id, author_id, comment, created_at")
                                .eq("book_id", bid).order("created_at")
                                .execute().data or []
                            )
                            if comments:
                                for comment in comments:
                                    who = "You" if comment.get("author_id") == user_id else "Student"
                                    st.markdown(f"**{who}**")
                                    st.write(comment.get("comment", ""))
                                    st.caption(comment.get("created_at", ""))
                            else:
                                st.info("No comments yet. Start the discussion.")

                            with st.form(f"comment_form_{bid}"):
                                comment_text = st.text_area("Write a comment", max_chars=1000)
                                post_comment = st.form_submit_button("Post Comment")
                            if post_comment:
                                if not comment_text.strip():
                                    st.warning("Please write a comment before posting.")
                                else:
                                    supabase.table("book_comments").insert({
                                        "book_id": bid,
                                        "author_id": user_id,
                                        "comment": comment_text.strip()
                                    }).execute()
                                    st.success("Your comment was posted.")
                                    st.rerun()
                        except Exception as exc:
                            show_error("Could not load or post comments.", exc)
        except Exception as exc:
            show_error("Could not load the book listings.", exc)

    # ------------------------- WISHLIST -------------------------

    elif page == "My Wishlist":
        st.subheader("❤️ My Wishlist")
        try:
            rows = (
                supabase.table("wishlist").select("book_id")
                .eq("student_id", user_id).execute().data or []
            )
            if not rows:
                st.info("Your wishlist is empty. Browse books to add some.")
            for row in rows:
                bid = row["book_id"]
                book_rows = (
                    supabase.table("books")
                    .select("id, title, author, book_category, book_condition, listing_type, price, description, status")
                    .eq("id", bid).limit(1).execute().data or []
                )
                if not book_rows:
                    st.caption(f"Book ID {bid}: listing details are unavailable.")
                    continue
                book = book_rows[0]
                with st.container(border=True):
                    st.markdown(f"### 📘 {book.get('title') or 'Untitled'}")
                    st.write(f"**Author:** {book.get('author') or 'Not specified'}")
                    st.write(f"**Category:** {book.get('book_category') or 'Not specified'}")
                    st.write(f"**Condition:** {book.get('book_condition') or 'Not specified'}")
                    st.write(f"**Listing:** {book.get('listing_type') or 'Not specified'}")
                    st.write(f"**Price:** {display_price(book)}")
                    if book.get("description"):
                        st.write(book["description"])
                    if book.get("status") != "Available":
                        st.info("This book is no longer available.")
                    if st.button("💔 Remove from Wishlist", key=f"wish_remove_{bid}"):
                        try:
                            supabase.table("wishlist").delete().eq("student_id", user_id).eq("book_id", bid).execute()
                            st.success("Book removed from your wishlist.")
                            st.rerun()
                        except Exception as exc:
                            show_error("Could not remove this book.", exc)
        except Exception as exc:
            show_error("Could not load your wishlist.", exc)

    # ------------------------- ADD A BOOK -------------------------

    elif page == "Add a Book":
        st.subheader("➕ Add a Book")
        with st.form("add_book_form", clear_on_submit=True):
            title = st.text_input("Book title")
            author = st.text_input("Author name")
            category = st.selectbox("Book category", BOOK_CATEGORIES)

            if category == "Novels":
                subject = st.selectbox("Novel genre", NOVEL_TYPES)
                course_value, semester_value = "", None
            elif category == "General Books":
                subject = st.selectbox("Book type", GENERAL_BOOK_TYPES)
                course_value, semester_value = "", None
            else:
                subject = st.text_input("Subject")
                course_value = st.text_input("Course")
                semester_value = st.selectbox("Semester", [1, 2, 3, 4, 5, 6])

            condition = st.selectbox("Book condition", BOOK_CONDITIONS)
            listing = st.selectbox("What do you want to do?", LISTING_TYPES)
            price_value = st.number_input("Selling price (₹)", min_value=1.0, step=10.0) if listing == "Sell" else 0.0
            if listing == "Free":
                st.info("This book will be offered for free.")
            elif listing == "Exchange":
                st.info("Students can contact you to discuss an exchange.")
            description = st.text_area("Description", placeholder="Add useful details about the book.")
            add_clicked = st.form_submit_button("Add Book", use_container_width=True)

        if add_clicked:
            if not title.strip() or not author.strip():
                st.warning("Please enter both the book title and author.")
            elif category == "Semester Textbooks" and (not subject.strip() or not course_value.strip()):
                st.warning("Please enter the subject and course.")
            else:
                try:
                    supabase.table("books").insert({
                        "seller_id": user_id,
                        "title": title.strip(),
                        "author": author.strip(),
                        "subject": subject,
                        "course": course_value,
                        "semester": semester_value,
                        "book_category": category,
                        "book_condition": condition,
                        "listing_type": listing,
                        "price": price_value,
                        "description": description.strip(),
                        "status": "Available"
                    }).execute()
                    st.success("Your book was added successfully.")
                    st.rerun()
                except Exception as exc:
                    show_error("Could not add your book. Check that the books table columns match this app.", exc)

    # ------------------------- NEED A BOOK -------------------------

    elif page == "Need a Book":
        st.subheader("🔎 Need a Book")
        st.write("Post a request when you cannot find the book you need.")

        with st.form("need_book_form", clear_on_submit=True):
            req_title = st.text_input("Book title")
            req_author = st.text_input("Author name (optional)")
            req_category = st.selectbox("Book category", BOOK_CATEGORIES)

            if req_category == "Novels":
                req_subject = st.selectbox("Novel genre", NOVEL_TYPES)
                req_course, req_semester = "", None
            elif req_category == "General Books":
                req_subject = st.selectbox("Book type", GENERAL_BOOK_TYPES)
                req_course, req_semester = "", None
            else:
                req_subject = st.text_input("Subject")
                req_course = st.text_input("Course")
                req_semester = st.selectbox("Semester", [1, 2, 3, 4, 5, 6])

            req_description = st.text_area("Additional details")
            request_clicked = st.form_submit_button("Post Request", use_container_width=True)

        if request_clicked:
            if not req_title.strip():
                st.warning("Please enter the book title.")
            elif req_category == "Semester Textbooks" and (not req_subject.strip() or not req_course.strip()):
                st.warning("Please enter the subject and course.")
            else:
                try:
                    supabase.table("book_requests").insert({
                        "student_id": user_id,
                        "title": req_title.strip(),
                        "author": req_author.strip(),
                        "book_category": req_category,
                        "subject": req_subject,
                        "course": req_course,
                        "semester": req_semester,
                        "description": req_description.strip(),
                        "status": "Open"
                    }).execute()
                    st.success("Your book request was posted successfully.")
                    st.rerun()
                except Exception as exc:
                    show_error("Could not post your request. Check the book_requests table columns and required fields.", exc)

        st.divider()
        st.subheader("📋 Student Book Requests")
        try:
            requests = (
                supabase.table("book_requests").select("*")
                .order("created_at", desc=True).execute().data or []
            )
            if not requests:
                st.info("There are no book requests yet.")
            for req in requests:
                rid = req["id"]
                with st.container(border=True):
                    st.markdown(f"### 📖 {req.get('title') or 'Untitled'}")
                    st.write(f"**Category:** {req.get('book_category') or 'Not specified'}")
                    st.write(f"**Author:** {req.get('author') or 'Not specified'}")
                    st.write(f"**Subject / Type:** {req.get('subject') or 'Not specified'}")
                    st.write(f"**Course:** {req.get('course') or 'Not specified'}")
                    st.write(f"**Semester:** {req.get('semester') or 'Not specified'}")
                    st.write(f"**Status:** {req.get('status') or 'Open'}")
                    if req.get("description"):
                        st.write(req["description"])
                    if req.get("student_id") == user_id:
                        st.caption("Your request")
                        statuses = ["Open", "Fulfilled"]
                        current = req.get("status") if req.get("status") in statuses else "Open"
                        new_status = st.selectbox(
                            "Request status", statuses,
                            index=statuses.index(current),
                            key=f"req_status_{rid}"
                        )
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Update Status", key=f"req_update_{rid}", use_container_width=True):
                                try:
                                    supabase.table("book_requests").update({"status": new_status}).eq("id", rid).eq("student_id", user_id).execute()
                                    st.success("Request status updated.")
                                    st.rerun()
                                except Exception as exc:
                                    show_error("Could not update the request status.", exc)
                        with c2:
                            if st.button("Delete Request", key=f"req_delete_{rid}", use_container_width=True):
                                try:
                                    supabase.table("book_requests").delete().eq("id", rid).eq("student_id", user_id).execute()
                                    st.success("Your request was deleted.")
                                    st.rerun()
                                except Exception as exc:
                                    show_error("Could not delete your request.", exc)
        except Exception as exc:
            show_error("Could not load book requests.", exc)

    # ------------------------- DELIVERY ADDRESS -------------------------

    elif page == "Delivery Address":
        st.subheader("🏠 My Delivery Addresses")
        st.write("Save an address to use when ordering a book.")

        with st.form("address_form", clear_on_submit=True):
            receiver = st.text_input("Receiver name")
            address_phone = st.text_input("Mobile number", max_chars=10)
            address_line = st.text_area("House number, street and area")
            city = st.text_input("City")
            state = st.text_input("State")
            pincode = st.text_input("PIN code", max_chars=6)
            address_clicked = st.form_submit_button("Save Address", use_container_width=True)

        if address_clicked:
            if not all([receiver.strip(), address_phone.strip(), address_line.strip(), city.strip(), state.strip(), pincode.strip()]):
                st.warning("Please complete every address field.")
            elif not address_phone.strip().isdigit() or len(address_phone.strip()) != 10:
                st.warning("Enter a valid 10-digit mobile number.")
            elif not pincode.strip().isdigit() or len(pincode.strip()) != 6:
                st.warning("Enter a valid 6-digit PIN code.")
            else:
                try:
                    supabase.table("delivery_addresses").insert({
                        "student_id": user_id,
                        "full_name": receiver.strip(),
                        "phone": address_phone.strip(),
                        "address_line": address_line.strip(),
                        "city": city.strip(),
                        "state": state.strip(),
                        "pincode": pincode.strip()
                    }).execute()
                    st.success("Delivery address saved successfully.")
                    st.rerun()
                except Exception as exc:
                    show_error("Could not save the address. Check the delivery_addresses table and its RLS policy.", exc)

        st.divider()
        st.subheader("📍 Saved Addresses")
        try:
            addresses = (
                supabase.table("delivery_addresses").select(
                    "id, full_name, phone, address_line, city, state, pincode, created_at"
                ).eq("student_id", user_id).order("created_at", desc=True)
                .execute().data or []
            )
            if not addresses:
                st.info("You have not saved a delivery address yet.")
            for address in addresses:
                aid = address["id"]
                with st.container(border=True):
                    st.markdown(f"### {address.get('full_name') or 'Receiver'}")
                    st.write(f"📞 {address.get('phone') or ''}")
                    st.write(address.get("address_line") or "")
                    st.write(f"{address.get('city') or ''}, {address.get('state') or ''}")
                    st.write(f"PIN code: {address.get('pincode') or ''}")
                    if st.button("🗑️ Delete Address", key=f"address_delete_{aid}"):
                        try:
                            supabase.table("delivery_addresses").delete().eq("id", aid).eq("student_id", user_id).execute()
                            st.success("Address deleted.")
                            st.rerun()
                        except Exception as exc:
                            show_error("Could not delete this address. An existing order may be using it.", exc)
        except Exception as exc:
            show_error("Could not load your saved addresses.", exc)

    # ------------------------- MY ORDERS -------------------------

    elif page == "My Orders":
        st.subheader("📦 My Orders")
        st.caption("Demo order management only. This app does not process online payments or connect to a courier.")

        st.markdown("### 🛒 Place a New Order")
        try:
            available = (
                supabase.table("books").select(
                    "id, seller_id, title, author, listing_type, price"
                ).eq("status", "Available").in_("listing_type", ["Sell", "Free"])
                .execute().data or []
            )
            available = [b for b in available if b.get("seller_id") != user_id]
            addresses = (
                supabase.table("delivery_addresses").select(
                    "id, full_name, phone, address_line, city, state, pincode"
                ).eq("student_id", user_id).execute().data or []
            )

            if not available:
                st.info("There are no Sell or Free books available from other students.")
            elif not addresses:
                st.warning("Please save a delivery address before placing an order.")
            else:
                # Include IDs in labels so duplicate titles/addresses remain unique.
                book_labels = {
                    f"{b.get('title') or 'Untitled'} — {display_price(b)} (Book ID: {b['id']})": b
                    for b in available
                }
                address_labels = {
                    f"{a.get('full_name')} — {a.get('city')} — PIN {a.get('pincode')} (Address ID: {a['id']})": a
                    for a in addresses
                }
                with st.form("place_order_form"):
                    chosen_book_label = st.selectbox("Choose a book", list(book_labels.keys()))
                    chosen_address_label = st.selectbox("Choose delivery address", list(address_labels.keys()))
                    order_confirm = st.checkbox("I confirm that the selected book and delivery address are correct.")
                    place_clicked = st.form_submit_button("Place Order", use_container_width=True)

                if place_clicked:
                    if not order_confirm:
                        st.warning("Please confirm the book and delivery address.")
                    else:
                        chosen_book = book_labels[chosen_book_label]
                        chosen_address = address_labels[chosen_address_label]
                        try:
                            # Recheck availability immediately before inserting.
                            latest = get_book(chosen_book["id"])
                            if not latest or latest.get("status") != "Available" or latest.get("seller_id") == user_id:
                                st.error("This book is no longer available. Refresh the page and choose another book.")
                            else:
                                supabase.table("orders").insert({
                                    "book_id": latest["id"],
                                    "buyer_id": user_id,
                                    "seller_id": latest["seller_id"],
                                    "address_id": chosen_address["id"],
                                    "price": 0 if latest.get("listing_type") == "Free" else (latest.get("price") or 0),
                                    "status": "Placed"
                                }).execute()
                                st.success("Your order was placed successfully.")
                                st.rerun()
                        except Exception as exc:
                            show_error("Order could not be placed. The book may have just been ordered, or a database permission/policy may be blocking the request.", exc)
        except Exception as exc:
            show_error("Could not load available books or delivery addresses.", exc)

        st.divider()
        st.markdown("### 🛍️ Orders I Placed")
        try:
            buyer_orders = (
                supabase.table("orders").select("*").eq("buyer_id", user_id)
                .order("created_at", desc=True).execute().data or []
            )
            if not buyer_orders:
                st.info("You have not placed any orders yet.")
            for order in buyer_orders:
                with st.container(border=True):
                    details = get_book(order["book_id"])
                    st.markdown(f"**{details.get('title', 'Book details unavailable') if details else 'Book details unavailable'}**")
                    if details:
                        st.write(f"**Author:** {details.get('author') or 'Not available'}")
                    st.write(f"**Order ID:** {order.get('id')}")
                    st.write(f"**Amount:** ₹{order.get('price') or 0}")
                    status = order.get("status") or "Placed"
                    st.write(f"**Status:** {status}")
                    st.caption(f"Ordered on: {order.get('created_at') or 'Not available'}")
                    if status in ORDER_STATUSES:
                        step = ORDER_STATUSES.index(status)
                        st.progress((step + 1) / len(ORDER_STATUSES))
                        st.write("Tracking: " + " → ".join(
                            [f"**{s}**" if i <= step else s for i, s in enumerate(ORDER_STATUSES)]
                        ))
        except Exception as exc:
            show_error("Could not load the orders you placed. Check the orders SELECT policy.", exc)

        st.divider()
        st.markdown("### 📬 Orders I Received")
        try:
            seller_orders = (
                supabase.table("orders").select("*").eq("seller_id", user_id)
                .order("created_at", desc=True).execute().data or []
            )
            if not seller_orders:
                st.info("You have not received any orders yet.")
            for order in seller_orders:
                with st.container(border=True):
                    details = get_book(order["book_id"])
                    st.markdown(f"**{details.get('title', 'Book details unavailable') if details else 'Book details unavailable'}**")
                    st.write(f"**Order ID:** {order.get('id')}")
                    st.write(f"**Amount:** ₹{order.get('price') or 0}")
                    current = order.get("status") or "Placed"
                    st.write(f"**Current status:** {current}")

                    # Address access depends on the seller-address SELECT policy.
                    try:
                        delivery_rows = (
                            supabase.table("delivery_addresses").select(
                                "full_name, phone, address_line, city, state, pincode"
                            ).eq("id", order["address_id"]).limit(1).execute().data or []
                        )
                        if delivery_rows:
                            delivery = delivery_rows[0]
                            st.markdown("#### 🚚 Delivery details")
                            st.write(delivery.get("full_name") or "")
                            st.write(delivery.get("phone") or "")
                            st.write(delivery.get("address_line") or "")
                            st.write(f"{delivery.get('city') or ''}, {delivery.get('state') or ''}")
                            st.write(f"PIN: {delivery.get('pincode') or ''}")
                        else:
                            st.warning("The delivery address is not visible. Check the seller address SELECT policy.")
                    except Exception as exc:
                        show_error("Could not read the delivery address.", exc)

                    if current in ORDER_STATUSES:
                        new_status = st.selectbox(
                            "Update tracking status",
                            ORDER_STATUSES,
                            index=ORDER_STATUSES.index(current),
                            key=f"seller_order_status_{order['id']}"
                        )
                        if st.button("Save Tracking Update", key=f"seller_order_update_{order['id']}"):
                            try:
                                # Prevent moving the order backwards.
                                if ORDER_STATUSES.index(new_status) < ORDER_STATUSES.index(current):
                                    st.warning("Tracking cannot be moved backwards.")
                                else:
                                    supabase.table("orders").update({
                                        "status": new_status
                                    }).eq("id", order["id"]).eq("seller_id", user_id).execute()
                                    st.success("Order tracking status updated.")
                                    st.rerun()
                            except Exception as exc:
                                show_error("Could not update tracking. Check the seller UPDATE policy on the orders table.", exc)
        except Exception as exc:
            show_error("Could not load received orders. Check the orders SELECT policy.", exc)

    # ------------------------- EXCHANGE REQUESTS -------------------------

    elif page == "Exchange Requests":
        st.subheader("🔄 Exchange Requests")
        st.caption("Request an exchange by offering one of your own available books. No payment is processed here.")

        st.markdown("### Send an Exchange Request")
        try:
            exchange_books = (
                supabase.table("books").select("id, seller_id, title, author, listing_type, status")
                .eq("status", "Available").eq("listing_type", "Exchange")
                .execute().data or []
            )
            exchange_books = [b for b in exchange_books if b.get("seller_id") != user_id]
            my_books = (
                supabase.table("books").select("id, title, author")
                .eq("seller_id", user_id).eq("status", "Available")
                .execute().data or []
            )
            if not exchange_books:
                st.info("There are no Exchange books available from other students yet.")
            elif not my_books:
                st.warning("Add an available book under your account first. You need a book to offer in exchange.")
            else:
                target_labels = {f"{b.get('title') or 'Untitled'} (Book ID: {b['id']})": b for b in exchange_books}
                offer_labels = {f"{b.get('title') or 'Untitled'} (Book ID: {b['id']})": b for b in my_books}
                with st.form("send_exchange_request_form"):
                    target_label = st.selectbox("Book you want", list(target_labels.keys()))
                    offer_label = st.selectbox("Your book offered in return", list(offer_labels.keys()))
                    exchange_confirm = st.checkbox("I confirm that I want to send this exchange request.")
                    send_exchange = st.form_submit_button("Send Exchange Request", use_container_width=True)
                if send_exchange:
                    target = target_labels[target_label]
                    offered = offer_labels[offer_label]
                    if not exchange_confirm:
                        st.warning("Please confirm the exchange request.")
                    elif target["id"] == offered["id"]:
                        st.warning("You cannot offer the same book you are requesting.")
                    else:
                        try:
                            supabase.table("exchange_requests").insert({
                                "book_id": target["id"],
                                "requester_id": user_id,
                                "offered_book_id": offered["id"],
                                "status": "Pending"
                            }).execute()
                            st.success("Exchange request sent!")
                            st.rerun()
                        except Exception as exc:
                            show_error("Could not send the exchange request. Check the exchange_requests table policies.", exc)
        except Exception as exc:
            show_error("Could not load exchange books or your books.", exc)

        st.divider()
        st.markdown("### Requests I Received")
        try:
            received = supabase.table("exchange_requests").select("*").order("created_at", desc=True).execute().data or []
            received = [r for r in received if (get_book(r.get("book_id")) or {}).get("seller_id") == user_id]
            if not received:
                st.info("You have not received any exchange requests yet.")
            for req in received:
                wanted = get_book(req.get("book_id"))
                offered = get_book(req.get("offered_book_id"))
                with st.container(border=True):
                    st.write(f"**Your book:** {(wanted or {}).get('title', 'Unavailable')}")
                    st.write(f"**Offered book:** {(offered or {}).get('title', 'Unavailable')}")
                    st.write(f"**Request ID:** {req.get('id')}")
                    st.write(f"**Status:** {req.get('status', 'Pending')}")
                    if req.get("status") == "Pending":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Accept", key=f"exchange_accept_{req['id']}", use_container_width=True):
                                try:
                                    supabase.table("exchange_requests").update({"status": "Accepted"}).eq("id", req["id"]).execute()
                                    st.success("Exchange request accepted.")
                                    st.rerun()
                                except Exception as exc:
                                    show_error("Could not accept this request. Check the exchange request UPDATE policy.", exc)
                        with c2:
                            if st.button("Reject", key=f"exchange_reject_{req['id']}", use_container_width=True):
                                try:
                                    supabase.table("exchange_requests").update({"status": "Rejected"}).eq("id", req["id"]).execute()
                                    st.success("Exchange request rejected.")
                                    st.rerun()
                                except Exception as exc:
                                    show_error("Could not reject this request. Check the exchange request UPDATE policy.", exc)
        except Exception as exc:
            show_error("Could not load received exchange requests. Check the exchange_requests SELECT policy.", exc)

        st.divider()
        st.markdown("### Requests I Sent")
        try:
            sent = supabase.table("exchange_requests").select("*").eq("requester_id", user_id).order("created_at", desc=True).execute().data or []
            if not sent:
                st.info("You have not sent any exchange requests yet.")
            for req in sent:
                wanted = get_book(req.get("book_id"))
                offered = get_book(req.get("offered_book_id"))
                with st.container(border=True):
                    st.write(f"**Book requested:** {(wanted or {}).get('title', 'Unavailable')}")
                    st.write(f"**Your offered book:** {(offered or {}).get('title', 'Unavailable')}")
                    st.write(f"**Status:** {req.get('status', 'Pending')}")
        except Exception as exc:
            show_error("Could not load your sent exchange requests.", exc)

    # ------------------------- LOGOUT -------------------------

    elif page == "Logout":
        st.subheader("👋 Logout")
        st.write("Are you sure you want to log out of BookBuddy?")
        if st.button("Yes, log out", type="primary", use_container_width=True):
            logout()
