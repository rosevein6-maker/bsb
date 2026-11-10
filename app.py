"""쇼핑리스트 앱 (Streamlit 단일 파일)."""

import json
from pathlib import Path
from uuid import uuid4

import streamlit as st

DATA_FILE = Path(__file__).parent / "data.json"
MAX_NAME_LEN = 50


# ---------- 저장 계층 ----------

def load_items() -> list[dict]:
    """data.json에서 아이템 목록을 읽는다. 파일이 없거나 깨졌으면 빈 리스트."""
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def save_items(items: list[dict]) -> None:
    """아이템 목록을 data.json에 저장한다."""
    DATA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- 상태 ----------

def init_state() -> None:
    """session_state를 초기화한다."""
    defaults = {
        "shopping_items": load_items,
        "editing_id": lambda: None,
        "add_error": lambda: None,   # 추가 폼 경고 메시지
        "edit_error": lambda: None,  # 수정 중 경고 메시지
    }
    for key, factory in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = factory()


def new_item(name: str) -> dict:
    """새 아이템 dict를 만든다."""
    return {"id": str(uuid4()), "name": name, "checked": False}


def set_items(items: list[dict]) -> None:
    """목록을 교체하고 파일에 저장한다."""
    st.session_state.shopping_items = items
    save_items(items)


def validate_name(raw: str | None) -> tuple[str | None, str | None]:
    """이름을 검증한다. (정리된 이름, 오류 메시지) 중 하나만 값이 있다."""
    name = (raw or "").strip()
    if not name:
        return None, "아이템 이름을 입력해주세요."
    if len(name) > MAX_NAME_LEN:
        return None, f"아이템 이름은 {MAX_NAME_LEN}자 이하로 입력해주세요."
    return name, None


# ---------- 기능 (콜백) ----------

def add_item() -> None:
    """입력값을 검증하고 아이템을 추가한다."""
    name, error = validate_name(st.session_state.get("new_name"))
    st.session_state.add_error = error
    if name:
        set_items(st.session_state.shopping_items + [new_item(name)])


def start_edit(item_id: str) -> None:
    """해당 아이템을 수정 모드로 전환한다. (한 번에 하나만)"""
    st.session_state.editing_id = item_id
    st.session_state.edit_error = None


def save_edit(item_id: str) -> None:
    """수정한 이름을 검증하고 저장한다."""
    name, error = validate_name(st.session_state.get(f"edit_name_{item_id}"))
    if error:
        st.session_state.edit_error = error
        return
    set_items([
        {**it, "name": name} if it["id"] == item_id else it
        for it in st.session_state.shopping_items
    ])
    cancel_edit()


def cancel_edit() -> None:
    """수정 모드를 종료한다."""
    st.session_state.editing_id = None
    st.session_state.edit_error = None


def delete_item(item_id: str) -> None:
    """해당 아이템을 삭제한다."""
    set_items([it for it in st.session_state.shopping_items if it["id"] != item_id])
    if st.session_state.editing_id == item_id:
        cancel_edit()


def toggle_item(item_id: str) -> None:
    """체크박스 값을 아이템의 checked에 반영한다."""
    checked = st.session_state[f"chk_{item_id}"]
    set_items([
        {**it, "checked": checked} if it["id"] == item_id else it
        for it in st.session_state.shopping_items
    ])


def clear_checked() -> None:
    """체크된 아이템을 모두 삭제한다."""
    items = st.session_state.shopping_items
    if st.session_state.editing_id in {it["id"] for it in items if it["checked"]}:
        cancel_edit()
    set_items([it for it in items if not it["checked"]])


# ---------- 화면 ----------

CSS = """
<style>
/* 좁은 화면에서도 행(체크·이름·버튼)이 세로로 쌓이지 않게 */
[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
[data-testid="stColumn"] { min-width: 0 !important; }

/* 아이템 이름 */
.item-name { word-break: break-word; overflow-wrap: anywhere; line-height: 1.4; }
.item-name.done { text-decoration: line-through; opacity: 0.45; }

/* 빈 목록 안내 */
.empty { text-align: center; padding: 2.5rem 0; opacity: 0.6; }
.empty .icon { font-size: 2.5rem; }

/* 진행 현황 텍스트 */
.progress-text { text-align: right; font-size: 0.9rem; opacity: 0.75; margin-bottom: -0.5rem; }
</style>
"""

# HTML·마크다운 특수문자 → 숫자 엔티티 (한 번에 변환해야 엔티티가 이중 변환되지 않음)
_ESCAPE_TABLE = str.maketrans(
    {c: f"&#{ord(c)};" for c in "&<>\"'\\`*_{}[]()#+-.!~|$"}
)


def safe_text(text: str) -> str:
    """사용자 입력을 HTML·마크다운으로 해석되지 않는 안전한 텍스트로 바꾼다."""
    return text.translate(_ESCAPE_TABLE)


def inject_css() -> None:
    """앱 전체 CSS를 주입한다."""
    st.markdown(CSS, unsafe_allow_html=True)


def render_progress(done: int, total: int) -> None:
    """진행 현황(텍스트 + 바)을 그린다."""
    st.markdown(
        f'<div class="progress-text">{done} / {total} 완료</div>',
        unsafe_allow_html=True,
    )
    st.progress(done / total if total else 0.0)
    if total and done == total:
        st.success("🎉 장보기 완료!")


def render_item(it: dict) -> None:
    """아이템 한 행을 그린다. 수정 중이면 입력창으로 표시."""
    item_id = it["id"]

    if st.session_state.editing_id == item_id:
        col_input, col_save, col_cancel = st.columns(
            [6, 0.8, 0.8], gap="small", vertical_alignment="center"
        )
        col_input.text_input(
            "이름 수정",
            value=it["name"],
            key=f"edit_name_{item_id}",
            max_chars=MAX_NAME_LEN,
            label_visibility="collapsed",
        )
        col_save.button("💾", key=f"save_{item_id}", help="저장",
                        type="tertiary", on_click=save_edit, args=(item_id,))
        col_cancel.button("↩️", key=f"cancel_{item_id}", help="취소",
                          type="tertiary", on_click=cancel_edit)
        if st.session_state.edit_error:
            st.warning(st.session_state.edit_error)
        return

    col_chk, col_name, col_edit, col_del = st.columns(
        [0.5, 5.2, 0.8, 0.8], gap="small", vertical_alignment="center"
    )
    col_chk.checkbox(
        it["name"],
        value=it["checked"],
        key=f"chk_{item_id}",
        on_change=toggle_item,
        args=(item_id,),
        label_visibility="collapsed",
    )
    done_cls = " done" if it["checked"] else ""
    col_name.markdown(
        f'<div class="item-name{done_cls}">{safe_text(it["name"])}</div>',
        unsafe_allow_html=True,
    )
    col_edit.button("✏️", key=f"edit_{item_id}", help="수정",
                    type="tertiary", on_click=start_edit, args=(item_id,))
    col_del.button("🗑️", key=f"del_{item_id}", help="삭제",
                   type="tertiary", on_click=delete_item, args=(item_id,))


def main() -> None:
    """화면을 그린다."""
    st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")
    inject_css()
    init_state()
    items = st.session_state.shopping_items
    done = sum(1 for it in items if it["checked"])

    st.title("🛒 쇼핑리스트")
    render_progress(done, len(items))

    # 입력 영역
    with st.form("add_form", clear_on_submit=True, border=False):
        col_input, col_btn = st.columns([5, 1.2], gap="small", vertical_alignment="center")
        col_input.text_input(
            "아이템",
            key="new_name",
            max_chars=MAX_NAME_LEN,
            placeholder="살 물건을 입력하세요",
            label_visibility="collapsed",
        )
        col_btn.form_submit_button("추가", type="primary",
                                   on_click=add_item, use_container_width=True)
    if st.session_state.add_error:
        st.warning(st.session_state.add_error)
        st.session_state.add_error = None

    st.divider()

    # 목록 영역
    if not items:
        st.markdown(
            '<div class="empty"><div class="icon">🧺</div>'
            "아직 추가된 아이템이 없어요.</div>",
            unsafe_allow_html=True,
        )
    else:
        for it in items:
            render_item(it)

        st.divider()
        _, col_clear = st.columns([2, 1.4])
        col_clear.button(
            "완료 항목 삭제",
            key="clear_checked",
            help="체크된 아이템을 모두 삭제합니다",
            on_click=clear_checked,
            disabled=done == 0,
            use_container_width=True,
        )


main()
