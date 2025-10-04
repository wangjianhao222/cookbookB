"""
Simple Streamlit Cookbook app (single-file)
- Add / list / view / delete recipes
- Stores data in ./data/recipes.json and images in ./data/images/

How to run:
1. pip install streamlit
2. streamlit run streamlit_cookbook_app.py

This file is intended for server deployment (no tkinter).
"""

import streamlit as st
from pathlib import Path
import json
import uuid
import datetime
import io

# --- Configuration ---
DATA_DIR = Path("data")
IMAGES_DIR = DATA_DIR / "images"
RECIPES_FILE = DATA_DIR / "recipes.json"

for p in (DATA_DIR, IMAGES_DIR):
    p.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Cookbook", layout="centered")

# --- Helpers ---

def load_recipes():
    if RECIPES_FILE.exists():
        try:
            with RECIPES_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_recipes(recipes):
    with RECIPES_FILE.open("w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)


def add_recipe(title, ingredients, steps, tags, image_bytes, image_name):
    recipes = load_recipes()
    rid = uuid.uuid4().hex
    image_filename = None
    if image_bytes is not None and image_name:
        ext = Path(image_name).suffix or ".jpg"
        image_filename = f"{rid}{ext}"
        (IMAGES_DIR / image_filename).write_bytes(image_bytes)

    recipes[rid] = {
        "id": rid,
        "title": title,
        "ingredients": ingredients,
        "steps": steps,
        "tags": tags,
        "image": image_filename,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    save_recipes(recipes)


def delete_recipe(rid):
    recipes = load_recipes()
    r = recipes.pop(rid, None)
    if r and r.get("image"):
        img_path = IMAGES_DIR / r["image"]
        try:
            img_path.unlink()
        except Exception:
            pass
    save_recipes(recipes)


def export_recipes_bytes():
    """Return the JSON bytes for download."""
    recipes = load_recipes()
    return json.dumps(recipes, ensure_ascii=False, indent=2).encode("utf-8")


# --- UI ---
st.title("🍳 简单食谱管理 (Streamlit)")

st.markdown(
    """
    **说明**: 这是一个单文件的 Streamlit 应用，用于添加 / 查看 / 删除食谱。数据保存在 `./data/recipes.json`，图片保存在 `./data/images/`。
    """
)

# Top: add recipe form
with st.expander("➕ 添加新食谱", expanded=True):
    with st.form("add_recipe_form"):
        title = st.text_input("标题", max_chars=120)
        ingredients_text = st.text_area(
            "材料（每行一个）", placeholder="例如：\n200g 面粉\n2 个鸡蛋"
        )
        steps = st.text_area("步骤", placeholder="写清楚制作步骤")
        tags_text = st.text_input("标签（用逗号分隔，例如：甜点, 快手）")
        image = st.file_uploader("可选：上传图片（jpg/png）", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("保存食谱")
        if submitted:
            if not title.strip():
                st.error("请填写标题。")
            else:
                ingredients = [l.strip() for l in ingredients_text.splitlines() if l.strip()]
                tags = [t.strip() for t in tags_text.split(",") if t.strip()]
                image_bytes = None
                image_name = None
                if image is not None:
                    image_bytes = image.read()
                    image_name = image.name
                add_recipe(title.strip(), ingredients, steps.strip(), tags, image_bytes, image_name)
                st.success("已保存！")

st.write("---")

# Sidebar: search & import/export
st.sidebar.header("搜索 / 数据导入导出")
search_q = st.sidebar.text_input("搜索标题 / 标签")

uploaded_json = st.sidebar.file_uploader("导入 recipes.json（可覆盖现有数据）", type=["json"])
if uploaded_json is not None:
    try:
        data = json.load(uploaded_json)
        save_recipes(data)
        st.sidebar.success("已导入并保存 recipes.json")
    except Exception as e:
        st.sidebar.error(f"导入失败: {e}")

st.sidebar.download_button(
    "下载 recipes.json",
    data=export_recipes_bytes(),
    file_name="recipes.json",
    mime="application/json",
)

# Load and filter recipes
recipes = load_recipes()
recipes_list = list(recipes.values())

if search_q:
    q = search_q.lower()
    recipes_list = [
        r
        for r in recipes_list
        if q in r.get("title", "").lower()
        or any(q in t.lower() for t in r.get("tags", []))
        or any(q in ing.lower() for ing in r.get("ingredients", []))
    ]

st.header(f"食谱列表 — 共 {len(recipes_list)} 项")

if not recipes_list:
    st.info("没有任何食谱。使用顶部的表单添加第一个食谱！")
else:
    for r in sorted(recipes_list, key=lambda x: x.get("created_at", ""), reverse=True):
        with st.expander(r.get("title", "(无标题)")):
            cols = st.columns([1, 2])
            with cols[0]:
                if r.get("image"):
                    img_path = IMAGES_DIR / r["image"]
                    if img_path.exists():
                        st.image(str(img_path), use_column_width=True)
                    else:
                        st.text("(图片丢失)")
                else:
                    st.text("(无图片)")
            with cols[1]:
                st.subheader(r.get("title"))
                if r.get("tags"):
                    st.write("标签:", ", ".join(r.get("tags")))
                if r.get("ingredients"):
                    st.write("**材料**")
                    for ing in r.get("ingredients"):
                        st.write("- ", ing)
                if r.get("steps"):
                    st.write("**步骤**")
                    st.write(r.get("steps"))

                btn_col1, btn_col2 = st.columns([1, 1])
                if btn_col1.button("删除", key=f"del_{r['id']}"):
                    delete_recipe(r["id"])
                    st.experimental_rerun()

                # 简单的导出单条食谱 JSON
                if btn_col2.download_button(
                    "导出 JSON",
                    data=json.dumps(r, ensure_ascii=False, indent=2).encode("utf-8"),
                    file_name=f"recipe_{r['id']}.json",
                    mime="application/json",
                    key=f"dl_{r['id']}",
                ):
                    pass

st.write("---")
st.caption("数据保存在应用根目录的 data/ 文件夹，图片保存在 data/images/。")

# Footer: small help
st.info("如需把桌面 tkinter 程序改成 Web，请把原来依赖 GUI 的逻辑（例如获取输入、显示图片）移植到本文件的表单和显示逻辑。需要帮忙我可以协助迁移现有代码。")
