from datetime import date, time
import pandas as pd
import streamlit as st

from cosmic_engine import BirthInput, Location, birth_chart, daily_alignment_text, panchangam_for_date, rank_muhurta_windows, ACTIVITY_PROFILES

st.set_page_config(page_title="Cosmic Analysis", page_icon="☀️", layout="wide")
st.title("☀️ Cosmic Analysis")
st.caption("Panchangam + Muhurta + Birth-Chart alignment dashboard")

PRESETS = {
    "San Jose, CA": Location("San Jose, CA", 37.3382, -121.8863, "America/Los_Angeles"),
    "Mumbai, India": Location("Mumbai, India", 19.0760, 72.8777, "Asia/Kolkata"),
    "Bengaluru, India": Location("Bengaluru, India", 12.9716, 77.5946, "Asia/Kolkata"),
    "Coimbatore, India": Location("Coimbatore, India", 11.0168, 76.9558, "Asia/Kolkata"),
    "New York, NY": Location("New York, NY", 40.7128, -74.0060, "America/New_York"),
}

with st.sidebar:
    st.header("Inputs")
    d = st.date_input("Date", value=date.today())
    preset = st.selectbox("Location preset", list(PRESETS))
    loc = PRESETS[preset]
    custom = st.checkbox("Override location")
    if custom:
        loc = Location(
            st.text_input("Place name", loc.name),
            st.number_input("Latitude", value=float(loc.latitude), format="%.6f"),
            st.number_input("Longitude", value=float(loc.longitude), format="%.6f"),
            st.text_input("Timezone", loc.timezone),
        )
    ayanamsha = st.selectbox("Ayanamsha", ["Lahiri", "Raman", "Krishnamurti"])
    activity = st.selectbox("Activity", list(ACTIVITY_PROFILES))
    slot_minutes = st.selectbox("Slot size", [15, 30, 45, 60], index=1)
    st.divider()
    use_birth = st.checkbox("Use birth-chart personalization")
    birth = None
    if use_birth:
        bd = st.date_input("Birth date", value=date(1990, 1, 1))
        bt = st.time_input("Birth time", value=time(12, 0))
        b_preset = st.selectbox("Birth place preset", list(PRESETS), index=1)
        b_loc = PRESETS[b_preset]
        birth = birth_chart(BirthInput(bd, bt, b_loc, ayanamsha))

result = rank_muhurta_windows(d, loc, activity, birth, ayanamsha, slot_minutes, top_n=12)
day = panchangam_for_date(d, loc, ayanamsha)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Tithi", f"{day.paksha} {day.tithi['name']}")
c2.metric("Nakshatra", f"{day.nakshatra['name']} P{day.nakshatra['pada']}")
c3.metric("Yoga", day.yoga["name"])
c4.metric("Karana", day.karana["name"])
c5.metric("Vara", day.vara)

st.subheader("Daily alignment")
for k, v in daily_alignment_text(day).items():
    st.write(f"**{k.title()}**: {v}")

st.subheader("Best Muhurta Windows")
rows = []
for w in result["top_windows"]:
    rows.append({
        "Start": w["start"][11:16],
        "End": w["end"][11:16],
        "Score": w["score"],
        "Band": w["band"],
        "Hora": w["hora_lord"],
        "Overlaps": ", ".join(w["overlaps"]),
        "Reasons": "; ".join(w["reasons"]),
        "Cautions": "; ".join(w["cautions"]),
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("Birth chart", expanded=use_birth):
    if birth:
        st.json(birth)
    else:
        st.info("Enable birth-chart personalization in the sidebar.")

with st.expander("Raw Panchangam JSON"):
    st.json(result)
