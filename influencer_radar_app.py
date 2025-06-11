import streamlit as st
import requests
import pandas as pd
import re
from io import BytesIO
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Influencer Radar", layout="wide")

with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown('<div class="animated-title">📡 Influencer Radar – Αναζήτησε & Ανάλυσε Δημόσια Προφίλ</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 Φίλτρα Αναζήτησης")
    platform = st.selectbox("Πλατφόρμα", ["Όλες", "Instagram", "TikTok", "YouTube"])
    country = st.selectbox("Χώρα", ["Όλες", "Κύπρος", "Ελλάδα", "Διεθνείς"])
    keyword = st.text_input("Λέξη-κλειδί (niche)", "fashion")
    only_sponsored = st.checkbox("Μόνο με Sponsored Posts")
    email_required = st.checkbox("Να έχουν email")

API_KEY = 'AIzaSyA6XiRfAWqtC_EKFXPGRJ_6EUs4QtnaV4M'
CX_ID = "63244caa4da064354"

def google_search(query, api_key, cx_id):
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={cx_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"API error: {response.status_code}")
        return []

def parse_followers(followers_str):
    if followers_str == "Άγνωστο":
        return np.nan
    followers_str = followers_str.upper().replace(",", ".").strip()
    multiplier = 1
    if "K" in followers_str:
        multiplier = 1_000
        followers_str = followers_str.replace("K", "")
    elif "Μ" in followers_str or "M" in followers_str:
        multiplier = 1_000_000
        followers_str = followers_str.replace("Μ", "").replace("M", "")
    try:
        return float(followers_str) * multiplier
    except:
        return np.nan

def analyze_snippet(snippet):
    followers_match = re.search(r"(\d+[\.,]?\d*[KΜ]?)\s*(followers|ακόλουθοι)", snippet, re.IGNORECASE)
    sponsored = any(x in snippet.lower() for x in ["sponsored", "συνεργασία", "διαφήμιση", "partnership", "ad"])
    email = ", ".join(set(re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", snippet)))
    return {
        "followers": followers_match.group(1) if followers_match else "Άγνωστο",
        "sponsored": "✅" if sponsored else "—",
        "email": email if email else "—"
    }

def extract_image(item):
    pagemap = item.get("pagemap", {})
    cse_image = pagemap.get("cse_image", [])
    if cse_image and isinstance(cse_image, list):
        return cse_image[0].get("src")
    og_image = pagemap.get("metatags", [])
    if og_image and isinstance(og_image, list):
        for tag in og_image:
            if "og:image" in tag:
                return tag["og:image"]
    return "https://via.placeholder.com/120?text=No+Image"

query = keyword
if platform != "Όλες":
    query += f" site:{platform.lower()}.com"
if country != "Όλες":
    query += f" {country}"

st.info("🔎 Εκτελείται αναζήτηση...")
results = google_search(query, API_KEY, CX_ID)
data = []

if results:
    for item in results:
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        info = analyze_snippet(snippet)
        img_url = extract_image(item)

        if only_sponsored and info["sponsored"] != "✅":
            continue
        if email_required and info["email"] == "—":
            continue

        data.append({
            "Όνομα": title,
            "Σύνδεσμος": link,
            "Followers Raw": info["followers"],
            "Followers": parse_followers(info["followers"]),
            "Sponsored": info["sponsored"],
            "Email": info["email"],
            "Bio": snippet,
            "Image": img_url
        })

    df = pd.DataFrame(data)

    if df.empty:
        st.warning("❌ Δεν βρέθηκαν αποτελέσματα με τα επιλεγμένα φίλτρα.")
    else:
        st.success(f"✅ Βρέθηκαν {len(df)} αποτελέσματα.")

        excel_file = BytesIO()
        df_to_export = df.drop(columns=["Image"])
        df_to_export.to_excel(excel_file, index=False, sheet_name="Influencers")
        excel_file.seek(0)

        st.download_button(
            label="📥 Κατέβασε τα αποτελέσματα σε Excel",
            data=excel_file,
            file_name="influencers.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        tabs = st.tabs(["📊 Πίνακας", "📈 Ανάλυση", "🧾 Κάρτες"])

        with tabs[0]:
            st.dataframe(df.drop(columns=["Image"]), use_container_width=True)

        with tabs[1]:
            fig = px.histogram(df, x="Followers", nbins=20, title="Κατανομή Ακολούθων")
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            for i, row in df.iterrows():
                card_html = f"""
                <div class=\"influencer-card\" onclick=\"window.open('{row['Σύνδεσμος']}', '_blank')\">
                    <img class=\"influencer-image\" src=\"{row['Image']}\" alt=\"Image\"/>
                    <div class=\"influencer-info\">
                        <div class=\"influencer-name\">{row['Όνομα']}</div>
                        <div class=\"influencer-details\">
                            <span>Followers: <b>{row['Followers Raw']}</b></span>
                            <span>Sponsored: {row['Sponsored']}</span>
                            <span>Email: {row['Email']}</span>
                        </div>
                        <div class=\"influencer-bio\">{row['Bio']}</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
else:
    st.warning("❌ Δεν επιστράφηκαν αποτελέσματα από την αναζήτηση.")
