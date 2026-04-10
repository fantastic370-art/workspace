import json
import os
import csv
from datetime import date, datetime, timedelta

import holidays
import streamlit as st
try:
    from streamlit_calendar import calendar as st_calendar
except Exception:
    st_calendar = None


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "my_data.json")
DEADLINES_CSV = os.path.join(APP_DIR, "data.csv")
# 과거 버전 호환용 경로(있으면 1회 마이그레이션에 사용)
LEGACY_JSON = os.path.join(os.path.expanduser("~"), "artist_dashboard_data.json")
LEGACY_CSV = os.path.join(os.path.expanduser("~"), "deadlines.csv")


def _read_deadlines_csv():
    if not os.path.exists(DEADLINES_CSV):
        return []
    rows = []
    try:
        with open(DEADLINES_CSV, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                name = (r.get("name") or "").strip()
                deadline = (r.get("deadline") or "").strip()
                if not name or not deadline:
                    continue
                proj = {
                    "name": name,
                    "deadline": deadline,
                    "start_date": (r.get("start_date") or date.today().strftime("%Y-%m-%d")).strip(),
                    "created": (r.get("created") or date.today().strftime("%Y-%m-%d")).strip(),
                    "category": (r.get("category") or "").strip(),
                    "steps_names": ["러프", "선화", "채색", "보정", "완성"],
                    "steps": [False, False, False, False, False],
                }
                rem = (r.get("remaining_qty") or "").strip()
                if rem:
                    try:
                        proj["remaining_qty"] = max(0, int(rem))
                    except Exception:
                        pass
                total = (r.get("total_qty") or "").strip()
                if total:
                    try:
                        proj["total_qty"] = max(0, int(total))
                    except Exception:
                        pass
                comp = (r.get("completed") or "").strip().lower()
                proj["completed"] = comp in ("1", "true", "yes", "y")
                rows.append(proj)
    except Exception:
        # CSV 파싱 실패 시 빈 목록 반환(앱 동작 우선)
        return []
    return rows


def _read_deadlines_csv_from(path):
    if not os.path.exists(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                name = (r.get("name") or "").strip()
                deadline = (r.get("deadline") or "").strip()
                if not name or not deadline:
                    continue
                proj = {
                    "name": name,
                    "deadline": deadline,
                    "start_date": (r.get("start_date") or date.today().strftime("%Y-%m-%d")).strip(),
                    "created": (r.get("created") or date.today().strftime("%Y-%m-%d")).strip(),
                    "category": (r.get("category") or "").strip(),
                    "steps_names": ["러프", "선화", "채색", "보정", "완성"],
                    "steps": [False, False, False, False, False],
                }
                rem = (r.get("remaining_qty") or "").strip()
                if rem:
                    try:
                        proj["remaining_qty"] = max(0, int(rem))
                    except Exception:
                        pass
                total = (r.get("total_qty") or "").strip()
                if total:
                    try:
                        proj["total_qty"] = max(0, int(total))
                    except Exception:
                        pass
                comp = (r.get("completed") or "").strip().lower()
                proj["completed"] = comp in ("1", "true", "yes", "y")
                rows.append(proj)
    except Exception:
        return []
    return rows


def _write_deadlines_csv(projects):
    fields = [
        "name",
        "deadline",
        "start_date",
        "created",
        "category",
        "remaining_qty",
        "total_qty",
        "completed",
    ]
    try:
        with open(DEADLINES_CSV, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for p in projects:
                w.writerow(
                    {
                        "name": p.get("name", ""),
                        "deadline": p.get("deadline", ""),
                        "start_date": p.get("start_date", ""),
                        "created": p.get("created", ""),
                        "category": p.get("category", ""),
                        "remaining_qty": p.get("remaining_qty", ""),
                        "total_qty": p.get("total_qty", ""),
                        "completed": "1" if p.get("completed", False) else "0",
                    }
                )
    except Exception as e:
        st.error(f"CSV 저장 실패: {e}")


def load_data():
    # 1) 현재 경로의 CSV가 있으면 우선 읽어와 프로젝트 데이터로 사용
    csv_projects = _read_deadlines_csv()
    if csv_projects:
        # CSV 우선 로드 시에도 JSON의 사용자 데이터(투두 등)는 유지
        persisted = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        persisted = raw
            except Exception:
                persisted = {}
        return {
            "projects": csv_projects,
            "daily_work": persisted.get("daily_work", {}),
            "theme": persisted.get("theme", "라벤더"),
            "username": persisted.get("username", "작가님"),
            "todos": persisted.get("todos", []),
            "daily_goal": persisted.get("daily_goal", 0),
        }

    # 2) 현재 경로 JSON 로드
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    # 3) 레거시 경로(홈 폴더) CSV/JSON 마이그레이션
    legacy_csv_projects = _read_deadlines_csv_from(LEGACY_CSV)
    if legacy_csv_projects:
        migrated = {
            "projects": legacy_csv_projects,
            "daily_work": {},
            "theme": "라벤더",
            "username": "작가님",
            "todos": [],
            "daily_goal": 0,
        }
        save_data(migrated)
        return migrated

    if os.path.exists(LEGACY_JSON):
        try:
            with open(LEGACY_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    save_data(data)
                    return data
        except Exception:
            pass
    return {
        "projects": [],
        "daily_work": {},
        "theme": "라벤더",
        "username": "작가님",
        "todos": [],
        "daily_goal": 0,
    }


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 프로젝트 변경은 deadlines.csv에도 즉시 동기화
        _write_deadlines_csv(data.get("projects", []))
    except Exception as e:
        st.error(f"저장 실패: {e}")


def days_left(deadline_str):
    try:
        d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return 999


def calc_working_days_kr(start_d: date, end_d: date) -> int:
    if end_d < start_d:
        return 0
    kr_holidays = holidays.KR(years=range(start_d.year, end_d.year + 1))
    cnt = 0
    cur = start_d
    while cur <= end_d:
        if cur.weekday() < 5 and cur not in kr_holidays:
            cnt += 1
        cur += timedelta(days=1)
    return cnt


def parse_date_ymd(value: str, fallback: date) -> date:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except Exception:
        return fallback


def parse_nonneg_int(value: str, fallback: int) -> int:
    try:
        return max(0, int(str(value).strip()))
    except Exception:
        return max(0, int(fallback))


@st.dialog("🧩 스케줄 추가")
def open_schedule_add_dialog(data):
    sched_type = st.selectbox("유형 선택", options=["커미션", "외주"], key="dlg_schedule_type")
    title = st.text_input("작품 제목", key="dlg_schedule_title", placeholder="예: 캐릭터 일러스트 / 브랜드 외주")
    due_date = st.date_input("마감일 선택", value=date.today() + timedelta(days=7), key="dlg_schedule_due")

    qty_str = "0"
    if sched_type == "외주":
        qty_str = st.text_input(
            "총 남은 수량 (외주 전용)",
            value=str(int(st.session_state.workload_remaining)),
            key="dlg_schedule_qty",
            placeholder="예: 120",
        )

    cols = st.columns([1, 1], gap="small")
    with cols[0]:
        if st.button("취소", use_container_width=True, key="dlg_cancel"):
            st.rerun()
    with cols[1]:
        if st.button("저장", use_container_width=True, key="dlg_save"):
            if title.strip():
                proj = {
                    "name": title.strip(),
                    "deadline": due_date.strftime("%Y-%m-%d"),
                    "start_date": date.today().strftime("%Y-%m-%d"),
                    "created": date.today().strftime("%Y-%m-%d"),
                    "category": sched_type,
                    "steps_names": ["러프", "선화", "채색", "보정", "완성"],
                    "steps": [False, False, False, False, False],
                }
                if sched_type == "외주":
                    parsed_qty = parse_nonneg_int(qty_str, st.session_state.workload_remaining)
                    proj["remaining_qty"] = parsed_qty
                    proj["total_qty"] = parsed_qty
                    st.session_state.workload_remaining = parsed_qty
                    st.session_state.workload_due = due_date
                data.setdefault("projects", []).append(proj)
                save_data(data)
                st.rerun()


@st.dialog("🗂️ 스케줄 관리")
def open_schedule_edit_dialog(data, real_idx: int):
    projects = data.get("projects", [])
    if real_idx < 0 or real_idx >= len(projects):
        st.markdown("해당 스케줄을 찾을 수 없습니다.")
        return

    p = projects[real_idx]
    st.markdown(f"**현재 항목:** {p.get('name', '제목 없음')} ({p.get('category', '기타')})")

    edit_title = st.text_input(
        "제목",
        value=p.get("name", ""),
        key=f"dlg_edit_title_{real_idx}",
        placeholder="작품 제목",
    )
    edit_deadline_str = st.text_input(
        "마감일",
        value=p.get("deadline", date.today().strftime("%Y-%m-%d")),
        key=f"dlg_edit_deadline_{real_idx}",
        placeholder="YYYY-MM-DD",
    )
    edit_category = st.selectbox(
        "카테고리",
        options=["커미션", "외주", "기타"],
        index=(["커미션", "외주", "기타"].index(p.get("category", "기타"))
               if p.get("category", "기타") in ["커미션", "외주", "기타"] else 2),
        key=f"dlg_edit_category_{real_idx}",
    )

    row1 = st.columns([1, 1], gap="small")
    with row1[0]:
        if st.button("수정 저장", use_container_width=True, key=f"dlg_save_{real_idx}"):
            projects[real_idx]["name"] = edit_title.strip() or "제목 없음"
            projects[real_idx]["deadline"] = parse_date_ymd(
                edit_deadline_str,
                parse_date_ymd(p.get("deadline", ""), date.today() + timedelta(days=7)),
            ).strftime("%Y-%m-%d")
            projects[real_idx]["category"] = edit_category
            save_data(data)
            st.rerun()
    with row1[1]:
        if st.button("완료", use_container_width=True, key=f"dlg_toggle_done_{real_idx}"):
            projects[real_idx]["completed"] = not bool(projects[real_idx].get("completed", False))
            save_data(data)
            st.rerun()

    row2 = st.columns([1, 1], gap="small")
    with row2[0]:
        if st.button("삭제", use_container_width=True, key=f"dlg_del_{real_idx}"):
            projects.pop(real_idx)
            save_data(data)
            st.rerun()
    with row2[1]:
        if st.button("닫기", use_container_width=True, key=f"dlg_close_{real_idx}"):
            st.rerun()


def init_session_state():
    if "workload_remaining" not in st.session_state:
        st.session_state.workload_remaining = 100
    if "workload_due" not in st.session_state:
        st.session_state.workload_due = date.today() + timedelta(days=7)
    if "heart_burst" not in st.session_state:
        st.session_state.heart_burst = False
    if "qty_undo_stack_by_project" not in st.session_state:
        st.session_state.qty_undo_stack_by_project = {}
    if "last_calendar_event" not in st.session_state:
        st.session_state.last_calendar_event = None


def apply_custom_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap');

        :root {
            --purple-main: #6A0DAD;
            --purple-light: #E6E6FA;
            --purple-neon: #A020F0;
            --bg-main: #F3E5F5;
            --text-main: #2D004D;
            --pink-accent: #E96ACB;
        }

        /* 브라우저/OS 다크모드와 무관하게 항상 밝은 테마 유지 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            color-scheme: light !important;
        }
        :root, :root * {
            color-scheme: light !important;
        }

        html, body, div, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            font-family: "Noto Sans KR", sans-serif !important;
            color: var(--text-main) !important;
        }

        [data-testid="stAppViewContainer"] {
            background: var(--bg-main);
        }

        p, span, label, div, li, small, strong, em {
            color: #2D004D !important;
        }

        [data-testid="stMarkdownContainer"] *,
        [data-testid="stText"],
        [data-testid="stCaptionContainer"] * {
            color: #2D004D !important;
        }

        h1, h2, h3 {
            font-weight: 800 !important;
            color: var(--purple-main) !important;
            margin-top: 0.2rem !important;
            margin-bottom: 0.35rem !important;
            font-size: 0.92rem !important;
        }
        .main-title {
            font-size: 2rem;
            font-weight: 800;
            color: #2D004D;
            margin: 0 0 0.7rem 0;
        }

        [data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--purple-light);
            border-radius: 25px;
            box-shadow: 0 4px 14px rgba(106, 13, 173, 0.10);
            padding: 6px 10px;
        }

        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--purple-main) !important;
            font-weight: 800;
        }

        [data-testid="stMetric"] [data-testid="stMetricLabel"] {
            color: #2D004D !important;
        }

        /* 카드 래퍼 통일 */
        .st-key-schedule_add_card,
        .st-key-schedule_manager_card,
        .st-key-workload_card,
        .st-key-calendar_card,
        .st-key-todo_card {
            background: rgba(255, 255, 255, 0.5) !important;
            border: 1px solid #E7D8EF !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important;
            padding: 1.45rem !important;
            min-height: 240px !important;
        }
        .st-key-schedule_add_card {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            min-height: auto !important;
        }

        .card-title {
            color: var(--purple-main);
            font-weight: 800;
            font-size: 0.84rem;
            margin-top: 0 !important;
            margin-bottom: 0.35rem !important;
        }

        [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"],
        [data-testid="column"] > div {
            gap: 0.8rem;
        }

        div.stButton > button,
        [data-testid="stButton"] > button {
            border-radius: 25px !important;
            background: none !important;
            background-color: #B892EA !important;
            background-image: none !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            border: none !important;
            font-weight: 800 !important;
            font-size: 0.84rem !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 6px 14px rgba(167, 125, 230, 0.22) !important;
        }
        div.stButton > button *,
        [data-testid="stButton"] > button * {
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-size: inherit !important;
            font-weight: inherit !important;
        }

        div.stButton > button:hover,
        [data-testid="stButton"] > button:hover {
            background: none !important;
            background-color: #A97DDF !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 14px rgba(167, 125, 230, 0.22) !important;
        }
        div.stButton > button:hover *,
        [data-testid="stButton"] > button:hover * {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            background: transparent !important;
        }

        div.stButton > button:focus,
        div.stButton > button:active,
        div.stButton > button:visited,
        div.stButton > button:focus *,
        div.stButton > button:active *,
        div.stButton > button:visited *,
        [data-testid="stButton"] > button:focus,
        [data-testid="stButton"] > button:active,
        [data-testid="stButton"] > button:focus *,
        [data-testid="stButton"] > button:active * {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }

        div.stButton > button[kind="primary"] {
            font-size: 0.84rem !important;
            padding-top: 0.28rem !important;
            padding-bottom: 0.28rem !important;
            border-radius: 25px !important;
            background: none !important;
            background-color: #B892EA !important;
        }

        /* Streamlit default dark button background 제거 */
        div.stButton > button[style*="rgb(38, 39, 48)"],
        [data-testid="stButton"] > button[style*="rgb(38, 39, 48)"] {
            background: none !important;
            background-color: #B892EA !important;
            color: #FFFFFF !important;
        }

        /* 스케줄 추가 버튼은 중요 액션으로 크게 강조 */
        .st-key-schedule_add_card div.stButton > button,
        .st-key-schedule_add_card [data-testid="stButton"] > button {
            font-size: 0.96rem !important;
            font-weight: 800 !important;
            padding: 0.48rem 1.05rem !important;
            min-height: 44px !important;
            min-width: 180px !important;
            border-radius: 26px !important;
            box-shadow: 0 7px 16px rgba(167, 125, 230, 0.26) !important;
        }
        .st-key-schedule_add_card div.stButton > button:hover,
        .st-key-schedule_add_card [data-testid="stButton"] > button:hover {
            font-size: 0.96rem !important;
        }

        /* 입력창: 색상만 고정(레이아웃은 Streamlit 기본 사용) */
        .stTextInput input,
        input, textarea {
            color: #2D004D !important;
            -webkit-text-fill-color: #2D004D !important;
            background: #FFFFFF !important;
            padding: 0.5rem 0.7rem !important;
        }

        /* 배포 환경에서 Selectbox/Input 내부가 검게 보이는 문제 강제 해결 */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
        [data-testid="stSelectbox"] [data-baseweb="select"] span,
        [data-testid="stMultiSelect"] [data-baseweb="select"] span,
        [data-baseweb="select"] > div,
        [data-baseweb="select"] input,
        [data-baseweb="input"] > div,
        [data-baseweb="input"] input {
            background-color: #FFFFFF !important;
            color: #2D004D !important;
            -webkit-text-fill-color: #2D004D !important;
            caret-color: #2D004D !important;
            opacity: 1 !important;
        }

        [data-testid="stSelectbox"] svg,
        [data-testid="stMultiSelect"] svg {
            fill: #2D004D !important;
            color: #2D004D !important;
        }

        /* Checkbox 강제 스타일 */
        div[data-testid="stCheckbox"] > label > span:first-child {
            background-color: #FFFFFF !important;
            border: 1px solid #A020F0 !important;
        }

        /* Selectbox/Date/Input 내부 모든 레이어 강제 라이트 */
        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
        }
        input[role="combobox"],
        input[type="text"] {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
            color: #2D004D !important;
            -webkit-text-fill-color: #2D004D !important;
        }
        [data-baseweb="select"] *,
        [data-baseweb="input"] *,
        [data-testid="stDateInput"] *,
        [data-testid="stSelectbox"] *,
        [data-testid="stMultiSelect"] * {
            background-color: #FFFFFF !important;
            color: #2D004D !important;
            -webkit-text-fill-color: #2D004D !important;
            opacity: 1 !important;
        }

        /* WebKit 기본 강제 다크 스타일 무시 */
        input,
        textarea,
        select,
        [data-baseweb="input"] input,
        [data-baseweb="select"] input {
            -webkit-appearance: none !important;
            appearance: none !important;
        }

        /* transparent 잔여값 강제 제거 */
        [data-testid="stDateInput"] [data-baseweb="input"] > div,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
        [data-testid="stTextInput"] [data-baseweb="input"] > div,
        [data-testid="stNumberInput"] [data-baseweb="input"] > div {
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
        }

        [data-baseweb="popover"] *,
        [role="listbox"] *,
        [role="option"] * {
            background-color: #FFFFFF !important;
            color: #2D004D !important;
            -webkit-text-fill-color: #2D004D !important;
        }

        /* 시스템 다크모드가 켜져 있어도 입력 위젯은 무조건 라이트 */
        @media (prefers-color-scheme: dark) {
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea,
            [data-testid="stNumberInput"] input,
            [data-testid="stDateInput"] input,
            [data-testid="stTimeInput"] input,
            [data-testid="stSelectbox"] [data-baseweb="select"] > div,
            [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
            [data-testid="stSelectbox"] [data-baseweb="select"] span,
            [data-testid="stMultiSelect"] [data-baseweb="select"] span,
            [data-baseweb="select"] > div,
            [data-baseweb="select"] input,
            [data-baseweb="input"] > div,
            [data-baseweb="input"] input,
            [data-baseweb="popover"] *,
            [role="listbox"] *,
            [role="option"] * {
                background: #FFFFFF !important;
                background-color: #FFFFFF !important;
                color: #2D004D !important;
                -webkit-text-fill-color: #2D004D !important;
                opacity: 1 !important;
                text-shadow: none !important;
            }
        }

        [data-testid="stForm"] label,
        [data-testid="stForm"] p,
        [data-testid="stForm"] span,
        [data-testid="stForm"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] p,
        [data-testid="stTextInput"] span {
            color: #5D4037 !important;
            font-size: 0.84rem !important;
        }

        .big-kpi {
            color: #2D004D;
            font-size: 0.9rem;
            font-weight: 800;
            line-height: 1.3;
            margin: 2px 0;
        }

        .heart-burst {
            text-align: center;
            font-size: 1.35rem;
            color: #A020F0;
            margin-top: 4px;
            margin-bottom: 2px;
        }

        .top-note {
            color: #6A0DAD;
            font-weight: 700;
            margin-bottom: 2px;
            font-size: 0.85rem;
        }

        .calendar-host {
            display: block !important;
            height: auto;
            margin-top: 0 !important;
            overflow: hidden;
            background: transparent !important;
            padding: 0 !important;
            border: none !important;
        }

        /* 캘린더 컴포넌트 바깥 직사각 배경 제거 */
        .st-key-calendar_card [data-testid="stElementContainer"],
        .st-key-calendar_card [data-testid="stElementContainer"] > div,
        .st-key-calendar_card iframe {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
        .st-key-calendar_card {
            margin-left: 0 !important;
        }

        /* 입력 컴포넌트 간 물리적 간격만 유지 */
        [data-testid="stTextInput"] {
            margin-bottom: 0.35rem !important;
        }

        [data-testid="stAlert"] * {
            color: #2D004D !important;
        }
        [data-baseweb="input"],
        [data-baseweb="input"] * {
            border: none !important;
            outline: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_calendar_events(projects: list):
    events = []
    for p in projects:
        deadline = p.get("deadline", "")
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except Exception:
            continue
        d_left = days_left(deadline)
        if 8 <= d_left <= 14:
            dot_color = "#22C55E"  # green
        elif 3 <= d_left <= 7:
            dot_color = "#FACC15"  # yellow
        elif 0 <= d_left <= 3:
            dot_color = "#EF4444"  # red
        else:
            dot_color = "#6A0DAD"  # default purple
        done = bool(p.get("completed", False))
        events.append(
            {
                "title": f"{'✅' if done else '🔄'} {p.get('name', 'Untitled')}",
                "start": deadline,
                "end": deadline,
                "allDay": True,
                "color": dot_color if not done else "#A78BC8",
                "backgroundColor": dot_color if not done else "#A78BC8",
                "borderColor": dot_color if not done else "#A78BC8",
                "textColor": "#FFFFFF",
                "extendedProps": {
                    "deadline": deadline,
                    "state": "완료" if done else "진행중",
                },
            }
        )
    return events


def render_calendar(data):
    with st.container(key="calendar_card"):
        with st.container():
            st.markdown("### 📅 마감 캘린더")
            st.markdown(
                "<span style='font-size:0.78rem; color:#2D004D;'>"
                "<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:#22C55E;vertical-align:middle;margin-right:4px;'></span>여유"
                " &nbsp;|&nbsp; "
                "<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:#FACC15;vertical-align:middle;margin-right:4px;'></span>D-7 이내"
                " &nbsp;|&nbsp; "
                "<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:#EF4444;vertical-align:middle;margin-right:4px;'></span>D-3 이내"
                " &nbsp;|&nbsp; "
                "<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:#A78BC8;vertical-align:middle;margin-right:4px;'></span>완료"
                "</span>",
                unsafe_allow_html=True,
            )
            done_count = sum(1 for p in data.get("projects", []) if p.get("completed", False))
            st.markdown(
                f"<span style='font-size:0.78rem; color:#2D004D;'>완료한 일정 수: {done_count}</span>",
                unsafe_allow_html=True,
            )
            events = build_calendar_events(data.get("projects", []))
            cal_options = {
                "locale": "en-gb",
                "initialView": "dayGridMonth",
                "headerToolbar": {
                    "left": "prev,next",
                    "center": "",
                    "right": "title",
                },
                "height": 420,
                "editable": False,
                "selectable": False,
                "eventDisplay": "block",
                "eventTextColor": "#2D004D",
                "eventBackgroundColor": "#E6E6FA",
                "eventBorderColor": "#B38ADF",
                "dayHeaderFormat": {"weekday": "short"},
                "titleFormat": {"year": "numeric", "month": "numeric"},
                "dayMaxEvents": True,
                "firstDay": 1,
            }
            custom_css = """
            html, body {
                background: #FFFFFF !important;
                margin: 0 !important;
                padding: 0 !important;
                border-radius: 20px !important;
                overflow: hidden !important;
            }
            .fc-view-harness,
            .fc-scrollgrid,
            .fc-theme-standard td,
            .fc-theme-standard th {
                background: #FFFFFF !important;
            }
            .fc,
            .fc *,
            .fc-theme-standard,
            .fc-theme-standard * {
                color: #2D004D !important;
                font-size: 0.86rem !important;
            }
            .fc {
                border-radius: 20px;
                background: #FFFFFF;
                padding: 4px;
                box-shadow: none !important;
                overflow: hidden !important;
            }
            .fc .fc-toolbar-title {
                color: #2D004D !important;
                font-weight: 700;
                font-size: 1.02rem !important;
                margin-right: 12px !important;
                margin-top: 12px !important;
            }
            .fc .fc-button-primary {
                background-color: #E6E6FA !important;
                border-color: #B38ADF !important;
                color: #ffffff !important;
                border-radius: 18px !important;
                font-size: 0.78rem !important;
                padding: 0.2rem 0.45rem !important;
                pointer-events: auto !important;
                position: relative !important;
                z-index: 20 !important;
                margin-top: 12px !important;
            }
            .fc .fc-button-group .fc-button {
                margin-left: 4px !important;
                margin-right: 4px !important;
            }
            .fc .fc-button-primary,
            .fc .fc-button-primary * { color: #2D004D !important; }
            .fc .fc-toolbar,
            .fc .fc-toolbar-chunk,
            .fc .fc-button-group {
                pointer-events: auto !important;
                position: relative !important;
                z-index: 20 !important;
            }
            .fc .fc-daygrid-day-number {
                color: #2D004D !important;
                font-weight: 700;
                font-size: 0.78rem !important;
            }
            .fc .fc-col-header-cell-cushion { color: #2D004D !important; font-weight: 700; }
            /* 요일 라벨을 한국어로 교체(월~일) */
            .fc .fc-col-header-cell-cushion {
                font-size: 0 !important;
            }
            .fc .fc-col-header-cell:nth-child(1) .fc-col-header-cell-cushion::after { content: "월"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-col-header-cell:nth-child(2) .fc-col-header-cell-cushion::after { content: "화"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-col-header-cell:nth-child(3) .fc-col-header-cell-cushion::after { content: "수"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-col-header-cell:nth-child(4) .fc-col-header-cell-cushion::after { content: "목"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-col-header-cell:nth-child(5) .fc-col-header-cell-cushion::after { content: "금"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-col-header-cell:nth-child(6) .fc-col-header-cell-cushion::after { content: "토"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-col-header-cell:nth-child(7) .fc-col-header-cell-cushion::after { content: "일"; font-size: 0.78rem; color:#2D004D; }
            .fc .fc-event-title, .fc .fc-event-time, .fc .fc-event-main { color: #2D004D !important; }
            /* 달력 셀 내부에서는 텍스트 숨기고 점(아이콘)만 표시 */
            .fc .fc-daygrid-event .fc-event-title,
            .fc .fc-daygrid-event .fc-event-time,
            .fc .fc-daygrid-event .fc-event-main-frame {
                display: none !important;
            }
            .fc .fc-daygrid-event {
                border: none !important;
                width: 11px !important;
                height: 11px !important;
                border-radius: 999px !important;
                min-height: 11px !important;
                padding: 0 !important;
                margin: 0 auto !important;
                box-shadow: 0 0 0 1px #FFFFFF, 0 0 0 1.5px rgba(45,0,77,0.15) !important;
                overflow: hidden !important;
                cursor: pointer !important;
            }
            .fc .fc-daygrid-event-harness {
                position: absolute !important;
                left: 50% !important;
                top: 50% !important;
                transform: translate(-50%, -50%) !important;
                display: flex !important;
                justify-content: center !important;
                width: 34px !important;
                height: 34px !important;
                align-items: center !important;
                margin: 0 !important;
                cursor: pointer !important;
                z-index: 5 !important;
                pointer-events: auto !important;
            }
            .fc .fc-daygrid-day-bg,
            .fc .fc-highlight,
            .fc .fc-cell-shaded {
                pointer-events: none !important;
            }
            .fc .fc-daygrid-day.fc-day-selected,
            .fc .fc-daygrid-day:focus-within {
                background: #FFFFFF !important;
            }
            .fc .fc-daygrid-day-frame { min-height: 62px; }
            .fc .fc-daygrid-day.fc-day-today {
                background: #6A0DAD !important;
            }
            .fc .fc-daygrid-day.fc-day-today .fc-daygrid-day-number {
                color: #FFFFFF !important;
            }
            .fc .fc-daygrid-day.fc-day-selected,
            .fc .fc-daygrid-day:focus-within {
                background: #6A0DAD !important;
            }
            .fc .fc-daygrid-day.fc-day-selected .fc-daygrid-day-number,
            .fc .fc-daygrid-day:focus-within .fc-daygrid-day-number {
                color: #FFFFFF !important;
            }
            .fc .fc-daygrid-day { background: #FFFFFF !important; }
            .fc .fc-scrollgrid, .fc-theme-standard td, .fc-theme-standard th { border-color: #D9B8FF !important; }
            """
            if st_calendar is None:
                st.markdown("`streamlit-calendar` 설치 후 캘린더를 사용할 수 있어요. (`pip install streamlit-calendar`)")
                return

            state = st_calendar(events=events, options=cal_options, custom_css=custom_css, key="main_calendar")
            if events:
                click_info = state.get("eventClick") if isinstance(state, dict) else None
                if click_info and click_info.get("event"):
                    e = click_info["event"]
                    ex = e.get("extendedProps", {})
                    st.session_state.last_calendar_event = {
                        "title": e.get("title", ""),
                        "deadline": ex.get("deadline", "-"),
                        "state": ex.get("state", "-"),
                    }
                else:
                    # eventClick 누락 시 dateClick으로 보조 처리
                    date_info = state.get("dateClick") if isinstance(state, dict) else None
                    if date_info:
                        picked = str(date_info.get("dateStr") or date_info.get("date") or "")[:10]
                        if picked:
                            matched = [ev for ev in events if str(ev.get("start", ""))[:10] == picked]
                            if matched:
                                ev0 = matched[0]
                                ex0 = ev0.get("extendedProps", {})
                                extra = f" 외 {len(matched)-1}건" if len(matched) > 1 else ""
                                st.session_state.last_calendar_event = {
                                    "title": f"{ev0.get('title', '')}{extra}",
                                    "deadline": picked,
                                    "state": ex0.get("state", "-"),
                                }
                if st.session_state.last_calendar_event:
                    ev = st.session_state.last_calendar_event
                    st.markdown(
                        f"**선택 이벤트:** {ev.get('title', '')} | 마감: {ev.get('deadline', '-')} | 상태: {ev.get('state', '-')}"
                    )
            else:
                st.markdown("캘린더에 표시할 마감 데이터가 없습니다.")


def render_workload_dashboard(data):
    with st.container(key="workload_card"):
        with st.container():
            st.markdown("### 💜 다량 외주 작업량 계산기")
            outsource_pairs = [
                (i, p) for i, p in enumerate(data.get("projects", [])) if p.get("category") == "외주"
            ]
            if outsource_pairs:
                outsource_items = [p for _, p in outsource_pairs]
                options = [
                    f"{p.get('name', '제목 없음')} | 마감 {p.get('deadline', '-')}"
                    for p in outsource_items
                ]
                selected_label = st.selectbox("외주 일정 선택", options=options, key="outsource_calc_select")
                selected_idx = options.index(selected_label)
                selected_real_idx = outsource_pairs[selected_idx][0]
                selected = outsource_items[selected_idx]

                remaining = parse_nonneg_int(selected.get("remaining_qty", "0"), 0)
                total_qty = parse_nonneg_int(selected.get("total_qty", remaining), remaining)
                if total_qty < remaining:
                    # 수동 수정 등으로 remaining이 커진 경우 기준값을 자동 보정
                    total_qty = remaining
                    data["projects"][selected_real_idx]["total_qty"] = total_qty
                    save_data(data)
                due = parse_date_ymd(selected.get("deadline", ""), date.today() + timedelta(days=7))
                working_days = calc_working_days_kr(date.today(), due)
                per_day = (remaining / working_days) if working_days > 0 else float(remaining)
                per_week = per_day * 5.0  # 5영업일 기준 주간 평균 목표
                done_qty = max(0, total_qty - remaining)
                done_pct = 0.0 if total_qty <= 0 else min(100.0, (done_qty / total_qty) * 100.0)

                row = st.columns([1.0, 1.0, 1.0], gap="small")
                with row[0]:
                    st.markdown(f'<div class="big-kpi">오늘의 목표: {per_day:.1f}장</div>', unsafe_allow_html=True)
                with row[1]:
                    st.markdown(f'<div class="big-kpi">주간 평균: {per_week:.1f}장</div>', unsafe_allow_html=True)
                with row[2]:
                    st.markdown(f'<div class="big-kpi">남은 평일: {working_days}일</div>', unsafe_allow_html=True)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                btn_row = st.columns([1.0, 1.0], gap="small")
                with btn_row[0]:
                    if st.button("💜 완료", use_container_width=True, type="primary"):
                        project_key = str(selected_real_idx)
                        st.session_state.qty_undo_stack_by_project.setdefault(project_key, []).append(remaining)
                        # 기존 데이터에 total_qty가 없으면, 첫 완료 시점의 수량을 기준치로 고정
                        if "total_qty" not in data["projects"][selected_real_idx]:
                            data["projects"][selected_real_idx]["total_qty"] = remaining
                        data["projects"][selected_real_idx]["remaining_qty"] = max(0, remaining - 1)
                        save_data(data)
                        st.session_state.heart_burst = True
                        st.balloons()
                        st.rerun()
                with btn_row[1]:
                    if st.button("↩ 롤백", use_container_width=True, key="btn_qty_rollback", type="primary"):
                        project_key = str(selected_real_idx)
                        per_project_stack = st.session_state.qty_undo_stack_by_project.get(project_key, [])
                        if per_project_stack and 0 <= selected_real_idx < len(data.get("projects", [])):
                            prev_qty = parse_nonneg_int(per_project_stack.pop(), remaining)
                            data["projects"][selected_real_idx]["remaining_qty"] = prev_qty
                            st.session_state.qty_undo_stack_by_project[project_key] = per_project_stack
                            save_data(data)
                            st.rerun()

                if st.session_state.heart_burst:
                    st.session_state.heart_burst = False

                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                st.markdown("**완료 진행률**")
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:12px;">
                      <div style="
                        width:96px;height:96px;border-radius:50%;
                        background: conic-gradient(#A020F0 {done_pct:.2f}%, #E9D9F8 {done_pct:.2f}% 100%);
                        display:flex;align-items:center;justify-content:center;">
                        <div style="
                          width:66px;height:66px;border-radius:50%;
                          background:#FFFFFF;display:flex;align-items:center;justify-content:center;
                          color:#2D004D;font-weight:800;font-size:0.9rem;">
                          {done_pct:.0f}%
                        </div>
                      </div>
                      <div style="color:#2D004D;font-size:0.86rem;line-height:1.5;">
                        완료: <b>{done_qty}</b>장<br/>
                        남음: <b>{remaining}</b>장<br/>
                        전체: <b>{total_qty}</b>장
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("**외주 추가 목록**")
            if not outsource_pairs:
                st.markdown("등록된 외주가 없습니다.")
            else:
                for _, p in sorted(outsource_pairs, key=lambda x: x[1].get("deadline", "")):
                    deadline = p.get("deadline", "-")
                    title = p.get("name", "제목 없음")
                    qty = parse_nonneg_int(p.get("remaining_qty", "0"), 0)
                    st.markdown(f"- {title}  |  마감: {deadline}  |  남은 수량: {qty}")


def render_schedule_add_card(data):
    with st.container(key="schedule_add_card"):
        if st.button("스케줄 추가", use_container_width=False, key="btn_open_schedule_dialog", type="primary"):
            open_schedule_add_dialog(data)


def render_schedule_manager(data):
    with st.container(key="schedule_manager_card"):
        with st.container():
            st.markdown("### 🗂️ 등록된 스케줄 관리")
            projects = data.get("projects", [])
            if not projects:
                st.markdown("등록된 스케줄이 없습니다.")
                return

            tab_all, tab_comm, tab_out = st.tabs(["전체", "커미션", "외주"])
            urgency_css_rules = []

            def _render_project_list(filtered_projects, key_prefix):
                if not filtered_projects:
                    st.markdown("해당 유형의 스케줄이 없습니다.")
                    return

                for idx, p in enumerate(sorted(filtered_projects, key=lambda x: x.get("deadline", ""))):
                    # sorted로 보여주되 원본 index를 찾기 위해 식별값 비교
                    try:
                        real_idx = next(i for i, rp in enumerate(projects) if rp is p)
                    except Exception:
                        real_idx = idx

                    deadline_raw = str(p.get("deadline", "-"))
                    deadline_num = "".join(ch for ch in deadline_raw if ch.isdigit()) or "-"
                    button_key = f"{key_prefix}_open_{real_idx}"
                    d_left = days_left(deadline_raw)
                    if p.get("completed", False):
                        bg_color = "#DDD6E6"
                        dot_color = "#A78BC8"
                    elif 8 <= d_left <= 14:
                        bg_color = "#22C55E"
                        dot_color = "#22C55E"
                    elif 3 <= d_left <= 7:
                        bg_color = "#FACC15"
                        dot_color = "#FACC15"
                    elif 0 <= d_left <= 3:
                        bg_color = "#EF4444"
                        dot_color = "#EF4444"
                    else:
                        bg_color = "#E6E6FA"
                        dot_color = "#6A0DAD"
                    label = f"{p.get('name', '제목 없음')} | {deadline_num}"

                    urgency_css_rules.append(
                        f"""
                        button[id*="{button_key}"] {{
                            background-color: {bg_color} !important;
                            border-color: {bg_color} !important;
                            color: #FFFFFF !important;
                            -webkit-text-fill-color: #FFFFFF !important;
                        }}
                        button[id*="{button_key}"]:hover {{
                            filter: brightness(0.95) !important;
                        }}
                        """
                    )

                    row_icon, row_btn = st.columns([0.08, 0.92], gap="small")
                    with row_icon:
                        st.markdown(
                            (
                                f"<div style='display:flex;justify-content:center;align-items:center;height:38px;'>"
                                f"<span style='display:inline-block;width:11px;height:11px;border-radius:999px;"
                                f"background:{dot_color};'></span></div>"
                            ),
                            unsafe_allow_html=True,
                        )
                    with row_btn:
                        if st.button(label, use_container_width=True, key=button_key, type="primary"):
                            open_schedule_edit_dialog(data, real_idx)

            with tab_all:
                _render_project_list(projects, "all")
            with tab_comm:
                _render_project_list([p for p in projects if p.get("category", "") == "커미션"], "commission")
            with tab_out:
                _render_project_list([p for p in projects if p.get("category", "") == "외주"], "outsource")

            if urgency_css_rules:
                st.markdown(f"<style>{''.join(urgency_css_rules)}</style>", unsafe_allow_html=True)


def _add_todo_from_input(data):
    new_todo = str(st.session_state.get("todo_input_text", "")).strip()
    if not new_todo:
        return
    todos = data.setdefault("todos", [])
    lowered_new = new_todo.lower()
    if any(str(item).strip().lower() == lowered_new for item in todos):
        st.session_state["todo_input_text"] = ""
        return
    todos.append(new_todo)
    save_data(data)
    st.session_state["todo_input_text"] = ""


def render_todo_list(data):
    with st.container(key="todo_card"):
        st.markdown("### ✅ 투두 리스트")
        st.text_input(
            "할 일 입력",
            value="",
            placeholder="예: 피드백 반영하기 (엔터로 추가)",
            key="todo_input_text",
            on_change=_add_todo_from_input,
            args=(data,),
        )

        todos = data.get("todos", [])
        if not todos:
            st.markdown("등록된 투두가 없습니다.")
            return

        for idx, todo in enumerate(list(todos)):
            checked = st.checkbox(todo, value=False, key=f"todo_check_{idx}")
            if checked:
                data["todos"].pop(idx)
                save_data(data)
                st.rerun()


def main():
    st.set_page_config(page_title="일정 관리", page_icon="🎨", layout="wide")
    init_session_state()
    apply_custom_theme()
    data = load_data()

    top_left, _top_right = st.columns([0.25, 0.75], gap="small")
    with top_left:
        render_schedule_add_card(data)
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    col_schedule, col_calendar, col_workload, col_todo = st.columns([1, 1, 1, 1], gap="small")
    with col_schedule:
        with st.container():
            render_schedule_manager(data)
    with col_calendar:
        with st.container():
            render_calendar(data)
    with col_workload:
        with st.container():
            render_workload_dashboard(data)
    with col_todo:
        with st.container():
            render_todo_list(data)


if __name__ == "__main__":
    main()
