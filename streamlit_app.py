"""
AI花束定制平台 - 完整合并版（Streamlit Cloud可部署）
保留所有原功能：花材推荐、花束描述生成、学校LLM API调用、订单系统
新增：推荐结果自动包含各类花材、提示词带数量和风格、根据风格变换包材
"""
import streamlit as st
import requests as http_requests
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ========== 页面配置 ==========
st.set_page_config(
    page_title="AI花束定制 | 智能花艺设计平台",
    page_icon="💐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== API配置 ==========
try:
    API_KEY = st.secrets.get("ECNU_API_KEY", os.getenv("ECNU_API_KEY", ""))
    API_BASE = st.secrets.get("ECNU_API_BASE", os.getenv("ECNU_API_BASE", "https://chat.ecnu.edu.cn/open/api/v1"))
    MODEL_NAME = st.secrets.get("ECNU_MODEL", os.getenv("ECNU_MODEL", "ecnu-plus"))
except:
    API_KEY = os.getenv("ECNU_API_KEY", "")
    API_BASE = os.getenv("ECNU_API_BASE", "https://chat.ecnu.edu.cn/open/api/v1")
    MODEL_NAME = os.getenv("ECNU_MODEL", "ecnu-plus")

# ========== CSS ==========
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fff9fb 0%, #fff5f8 100%); }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #ff6b9d, #8b5cf6); border-radius: 10px; }
    .main-header {
        text-align: center; padding: 40px 20px 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 0 0 30px 30px; margin: -60px -50px 30px -50px;
        color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .flower-item {
        background: linear-gradient(135deg, #fff 0%, #fef5f7 100%);
        border-radius: 20px; padding: 20px;
        border: 1px solid rgba(255,107,157,0.2);
        transition: all 0.3s ease; cursor: pointer; height: 100%;
    }
    .flower-item:hover { transform: translateY(-5px); border-color: #ff6b9d; box-shadow: 0 10px 25px rgba(255,107,157,0.15); }
    .flower-visual {
        width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 12px;
        background: conic-gradient(from 0deg, #ff6b9d, #8b5cf6, #667eea, #ff6b9d);
        display: flex; align-items: center; justify-content: center;
        font-size: 40px; box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    .flower-name { font-size: 18px; font-weight: bold; text-align: center; color: #333; margin-bottom: 6px; }
    .flower-language { font-size: 12px; text-align: center; color: #ff6b9d; margin-bottom: 10px; font-style: italic; }
    @keyframes bouquet-spin {
        0% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(180deg) scale(1.1); }
        100% { transform: rotate(360deg) scale(1); }
    }
    .loading-bouquet { animation: bouquet-spin 2s ease-in-out infinite; font-size: 60px; text-align: center; display: inline-block; }
    .ai-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 20px; border-radius: 20px; border-top-left-radius: 5px;
        margin: 20px 0; box-shadow: 0 5px 15px rgba(102,126,234,0.3);
    }
    .stButton > button {
        background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        color: white; border: none; border-radius: 40px;
        padding: 10px 20px; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,107,157,0.4); }
    .price-tag {
        display: inline-block; background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold;
    }
    .type-badge-main {
        display: inline-block; background: linear-gradient(135deg, #ff6b9d, #ff4081);
        color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    }
    .type-badge-filler {
        display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2);
        color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    }
    .type-badge-leaf {
        display: inline-block; background: linear-gradient(135deg, #10b981, #34d399);
        color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    }
    .type-badge-fruit {
        display: inline-block; background: linear-gradient(135deg, #f59e0b, #fbbf24);
        color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    }
    .footer {
        text-align: center; padding: 30px; margin-top: 50px;
        color: #999; font-size: 12px; border-top: 1px solid rgba(255,107,157,0.2);
    }
</style>
""", unsafe_allow_html=True)


# ========== RAG引擎 ==========
class FlowerRAGEngine:
    def __init__(self):
        try:
            knowledge_path = os.path.join(os.path.dirname(__file__), "knowledge_base", "flower_knowledge.json")
            with open(knowledge_path, "r", encoding="utf-8") as f:
                self.flower_data = json.load(f)
        except FileNotFoundError:
            knowledge_path = os.path.join(os.path.dirname(__file__), "flower_knowledge.json")
            with open(knowledge_path, "r", encoding="utf-8") as f:
                self.flower_data = json.load(f)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.flower_data:
            return []
        query = query.lower()
        keywords = set(query.replace("、", " ").split())
        scored_flowers = []
        for flower in self.flower_data:
            score = 0
            search_text = (flower.get("name", "") + flower.get("color", "") + flower.get("language", "") + " ".join(flower.get("occasion", [])) + " ".join(flower.get("target", [])) + flower.get("style", "") + flower.get("description", "")).lower()
            for kw in keywords:
                if kw in search_text:
                    score += 1
            if score > 0:
                scored_flowers.append((score, flower))
        scored_flowers.sort(key=lambda x: x[0], reverse=True)
        results = []
        for i in range(min(top_k, len(scored_flowers))):
            results.append(scored_flowers[i][1].copy())
        return results
    
    def search_by_category(self, query: str, category: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """按类别搜索花材（主花/配花/叶材/果材）"""
        all_results = self.search(query, top_k=top_k * 2)
        filtered = [f for f in all_results if f.get("category") == category]
        return filtered[:top_k]


rag_engine = FlowerRAGEngine()


# ========== 花材分类函数 ==========
def get_flower_category(flower: Dict) -> str:
    """获取花材的分类（主花/配花/叶材/果材）"""
    category = flower.get("category", "")
    if category in ["主花", "配花", "叶材", "果材"]:
        return category
    
    # 根据名称推断（后备逻辑）
    name = flower.get("name", "")
    leaf_keywords = ['叶', '草', '蕨', '松', '竹', '尤加利', '喷泉', '龟背', '散尾', '蓬莱', '排草', '羊齿', '剑叶', '栀子叶', '龙柳', '红瑞木']
    filler_keywords = ['满天星', '勿忘我', '情人草', '水晶草', '蕾丝', '翠珠', '风铃', '蓝星', '松虫', '鼠尾', '相思梅', '翠菊', '波斯菊', '黄金球', '澳洲米花']
    fruit_keywords = ['红豆', '冬青', '火棘', '灯笼果', '蔷薇果', '棉花', '蒲棒', '芦苇']
    name_lower = name.lower()
    if any(kw in name_lower for kw in leaf_keywords):
        return '叶材'
    elif any(kw in name_lower for kw in filler_keywords):
        return '配花'
    elif any(kw in name_lower for kw in fruit_keywords):
        return '果材'
    else:
        return '主花'


def get_category_emoji(category: str) -> str:
    """获取分类对应的emoji"""
    emoji_map = {
        '主花': '🌹',
        '配花': '✨',
        '叶材': '🍃',
        '果材': '🍎'
    }
    return emoji_map.get(category, '💐')


def get_category_badge(category: str) -> str:
    """获取分类对应的CSS类"""
    badge_map = {
        '主花': 'type-badge-main',
        '配花': 'type-badge-filler',
        '叶材': 'type-badge-leaf',
        '果材': 'type-badge-fruit'
    }
    class_name = badge_map.get(category, 'price-tag')
    return f'<span class="{class_name}">{get_category_emoji(category)} {category}</span>'


# ========== 推荐函数（自动包含各类花材） ==========
def recommend_flowers_balanced(target, occasion, color_preference, style, budget):
    """
    智能推荐花材，自动包含主花、配花、叶材、果材
    根据用户需求推荐不同类别的花材组合
    """
    query = f"{target} {occasion} {color_preference} {style} {budget}"
    
    # 推荐主花（2-3种）
    main_flowers = rag_engine.search_by_category(query, "主花", top_k=3)
    if len(main_flowers) < 2:
        # 如果不够，补充其他推荐
        additional = rag_engine.search(query, top_k=5)
        for f in additional:
            if get_flower_category(f) == "主花" and f not in main_flowers:
                main_flowers.append(f)
            if len(main_flowers) >= 3:
                break
    
    # 推荐配花（2-3种）
    filler_flowers = rag_engine.search_by_category(query, "配花", top_k=3)
    if len(filler_flowers) < 2:
        additional = rag_engine.search(query, top_k=5)
        for f in additional:
            if get_flower_category(f) == "配花" and f not in filler_flowers:
                filler_flowers.append(f)
            if len(filler_flowers) >= 3:
                break
    
    # 推荐叶材（1-2种）
    leaf_flowers = rag_engine.search_by_category(query, "叶材", top_k=2)
    if len(leaf_flowers) < 1:
        additional = rag_engine.search(query, top_k=3)
        for f in additional:
            if get_flower_category(f) == "叶材" and f not in leaf_flowers:
                leaf_flowers.append(f)
            if len(leaf_flowers) >= 2:
                break
    
    # 推荐果材（0-2种，根据场合）
    fruit_flowers = rag_engine.search_by_category(query, "果材", top_k=2)
    # 如果不是节日/年节场合，减少果材数量
    if occasion not in ["年节", "圣诞节", "春节", "乔迁"]:
        fruit_flowers = fruit_flowers[:1]
    
    # 合并所有推荐
    all_flowers = main_flowers + filler_flowers + leaf_flowers + fruit_flowers
    
    # 去重（按id）
    seen_ids = set()
    unique_flowers = []
    for f in all_flowers:
        if f["id"] not in seen_ids:
            seen_ids.add(f["id"])
            unique_flowers.append(f)
    
    # 确保每种类型都有推荐（如果某种类型缺失，用通用推荐补充）
    categories_found = {get_flower_category(f) for f in unique_flowers}
    
    if "主花" not in categories_found:
        default_main = rag_engine.search("浪漫 经典 花束", top_k=2)
        for f in default_main:
            if f not in unique_flowers:
                unique_flowers.insert(0, f)
                break
    
    if "配花" not in categories_found:
        default_filler = rag_engine.search("清新 点缀 花束", top_k=2)
        for f in default_filler:
            if f not in unique_flowers:
                unique_flowers.insert(2, f)
                break
    
    if "叶材" not in categories_found:
        default_leaf = [{"id": 999, "name": "尤加利叶", "color": "灰绿色", "language": "恩赐、回忆", "price_level": "低", "unit_price": 3, "category": "叶材", "description": "清新的桉树叶，提升花束质感"}]
        for f in default_leaf:
            if f not in unique_flowers:
                unique_flowers.append(f)
    
    # 生成AI推荐语
    prompt = f"""你是一个专业的花艺推荐师。请根据以下花材组合，写一段150字以内的推荐语。

推荐对象：{target}
场合：{occasion}
颜色偏好：{color_preference}
风格偏好：{style}

推荐花材组合：
主花：{[f['name'] for f in main_flowers]}
配花：{[f['name'] for f in filler_flowers]}
叶材：{[f['name'] for f in leaf_flowers]}
果材：{[f['name'] for f in fruit_flowers]}

请输出一段温暖有感染力的推荐语，说明为什么这个花材组合适合ta。"""

    recommendation_text = call_ecnu_llm("你是一位温暖专业的花艺推荐师。", prompt)
    if not recommendation_text:
        main_names = "、".join([f["name"] for f in main_flowers[:2]])
        filler_names = "、".join([f["name"] for f in filler_flowers[:2]])
        recommendation_text = f"🌷 为您精心设计了专属花束！主花选用{main_names}，搭配{filler_names}，整体风格{style}，{color_preference}色调与「{occasion}」场合完美契合。让这份花礼传达您的心意～"

    return {
        "success": True, 
        "flowers": unique_flowers,
        "main_flowers": main_flowers,
        "filler_flowers": filler_flowers,
        "leaf_flowers": leaf_flowers,
        "fruit_flowers": fruit_flowers,
        "recommendation": recommendation_text
    }


# ========== 根据风格获取包材描述 ==========
def get_wrapping_by_style(style: str) -> str:
    """根据风格返回对应的包装材料描述"""
    style_wrapping = {
        "浪漫": "elegant pink or red wrapping paper, soft silk ribbon, romantic style",
        "清新自然": "kraft paper, green leaf wrapping, natural jute twine, fresh natural style",
        "简约高级": "black or white minimalist wrapping paper, simple modern style, clean lines",
        "阳光活力": "bright yellow or orange wrapping paper, cheerful ribbon, vibrant energetic style",
        "复古": "vintage newspaper wrapping, antique lace ribbon, retro nostalgic style",
        "可爱": "cute polka dot wrapping paper, fluffy bow, kawaii cute style",
        "华丽大气": "luxurious gold foil wrapping, satin ribbon, opulent grand style",
        "温馨": "warm beige wrapping, soft fabric ribbon, cozy warm style"
    }
    return style_wrapping.get(style, "kraft paper wrapping with ribbon, classic style")


def get_bouquet_shape_by_style(style: str) -> str:
    """根据风格返回花束形状描述"""
    style_shape = {
        "浪漫": "round dome-shaped bouquet",
        "清新自然": "loose natural hand-tied bouquet",
        "简约高级": "asymmetrical modern bouquet",
        "阳光活力": "sunburst radiating bouquet",
        "复古": "cascade waterfall bouquet",
        "可爱": "compact round posy bouquet",
        "华丽大气": "large showy garden bouquet",
        "温馨": "soft gathered bouquet"
    }
    return style_shape.get(style, "elegant hand-tied bouquet")


# ========== LLM调用 ==========
def call_ecnu_llm(system_prompt: str, user_prompt: str, max_tokens: int = 300) -> str:
    if not API_KEY or API_KEY == "你的API密钥":
        return None
    try:
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        payload = {"model": MODEL_NAME, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.7, "max_tokens": max_tokens}
        resp = http_requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.warning(f"⚠️ LLM调用失败，将使用备用描述")
        return None


# ========== 生成花束描述（带数量和风格） ==========
def generate_bouquet_description_with_details(flower_quantities: Dict, selected_flowers: List, color_preference: str, style: str):
    """
    生成花束描述，包含每种花材的具体数量和风格相关的包材
    """
    if not selected_flowers:
        return {"success": False, "message": "请至少选择一种花材"}
    
    # 构建详细的花材列表（带数量）
    flower_details = []
    total_stems = 0
    for flower in selected_flowers:
        flower_id = flower["id"]
        quantity = flower_quantities.get(flower_id, get_default_quantity(flower, st.session_state.get("size", "M")))
        if quantity > 0:
            category = get_flower_category(flower)
            flower_details.append({
                "name": flower["name"],
                "quantity": quantity,
                "category": category,
                "color": flower.get("color", "").split("、")[0]
            })
            total_stems += quantity
    
    # 收集整体色调
    flower_colors = []
    for f in selected_flowers:
        color_field = f.get("color", "")
        for c in ['红色', '粉色', '白色', '黄色', '紫色', '蓝色', '绿色', '橙色', '香槟色']:
            if c in color_field:
                flower_colors.append(c)
    flower_colors = list(set(flower_colors))
    
    if color_preference and color_preference != "任意":
        color_keywords = color_preference
    elif flower_colors:
        color_keywords = "、".join(flower_colors[:2])
    else:
        color_keywords = "vibrant natural"
    
    # 获取风格对应的包材和形状
    wrapping_desc = get_wrapping_by_style(style)
    shape_desc = get_bouquet_shape_by_style(style)
    
    # 构建详细的花材列表字符串
    flower_list_str = ", ".join([f"{d['quantity']} stems of {d['name']}" for d in flower_details])
    
    # 构建完整提示词
    prompt = f"""请将以下花束设计转化为一段英文的花束描述，用于AI文生图工具生成花束图片。

花材详情（带数量）：
{flower_list_str}

总花材数量：{total_stems}支
整体色调：{color_keywords}
设计风格：{style}

包装要求：
- 花束形状：{shape_desc}
- 包装材料：{wrapping_desc}

要求：
- 必须包含每种花材的具体数量
- 必须体现「{color_keywords}」作为整体色调
- 必须使用「{shape_desc}」作为花束形状
- 必须使用「{wrapping_desc}」作为包装风格
- 包含 "fresh floral arrangement", "professional floral photography" 等关键词
- 输出纯英文，80词以内
- 示例格式："A beautiful bouquet of 3 red roses and 5 white lilies, arranged in a round dome-shaped bouquet, wrapped in kraft paper with jute twine..."
"""

    description = call_ecnu_llm("你擅长将花束设计转化为优美的英文描述，注意包含具体数量和包装细节。", prompt, max_tokens=250)
    
    if not description:
        # 备用描述
        flower_names_str = ", ".join([f"{d['quantity']} {d['name']}" for d in flower_details[:4]])
        description = f"A stunning {color_keywords} bouquet consisting of {flower_names_str}. Arranged in a {shape_desc}, wrapped with {wrapping_desc}. Fresh floral arrangement with layered textures, soft natural lighting, professional floral photography style, high quality, 8k."
    
    return {
        "success": True, 
        "description": description, 
        "flower_details": flower_details,
        "total_stems": total_stems,
        "color_theme": color_keywords,
        "style": style
    }


# ========== 辅助函数 ==========
def get_flower_emoji(flower_name):
    emoji_map = {
        '玫瑰': '🌹', '泡泡玫瑰': '🌹', '百合': '⚜️', '康乃馨': '🌸',
        '洋桔梗': '💐', '绣球': '🪻', '满天星': '⭐', '向日葵': '🌻',
        '郁金香': '🌷', '芍药': '🌺', '牡丹': '🌺', '勿忘我': '💜',
        '情人草': '💜', '扶郎花': '🌼', '小雏菊': '🌼', '乒乓菊': '⚪',
        '洋甘菊': '🌼', '茉莉花': '🤍', '栀子花': '🤍', '荷花': '🪷',
        '红豆': '❤️', '尤加利叶': '🌿', '龟背竹叶': '🌿', 'default': '💐'
    }
    return emoji_map.get(flower_name, emoji_map['default'])


def get_default_quantity(flower, size):
    flower_type = get_flower_category(flower)
    size_defaults = {
        'S': {'主花': 3, '配花': 2, '叶材': 2, '果材': 1},
        'M': {'主花': 5, '配花': 3, '叶材': 3, '果材': 2},
        'L': {'主花': 8, '配花': 5, '叶材': 5, '果材': 3},
        'XL': {'主花': 12, '配花': 8, '叶材': 8, '果材': 5}
    }
    return size_defaults.get(size, {}).get(flower_type, 3)


def get_min_quantity(flower, size):
    return 1


def get_max_quantity(flower, size):
    flower_type = get_flower_category(flower)
    size_max = {'S': 5, 'M': 10, 'L': 20, 'XL': 30}
    type_max = {'主花': size_max.get(size, 10), '配花': size_max.get(size, 10) * 2, '叶材': size_max.get(size, 10) * 2, '果材': size_max.get(size, 10)}
    return type_max.get(flower_type, 10)


def get_step(flower):
    flower_type = get_flower_category(flower)
    return 1 if flower_type == '主花' else 2


def calculate_bouquet_price(selected_flowers, flower_quantities, size):
    flower_cost = 0
    flower_detail = []
    for flower in selected_flowers:
        flower_id = flower["id"]
        quantity = flower_quantities.get(flower_id, 0)
        unit_price = flower.get("unit_price", 5)
        subtotal = quantity * unit_price
        flower_cost += subtotal
        flower_detail.append({
            "name": flower["name"],
            "type": get_flower_category(flower),
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal
        })
    packaging_cost = {'S': 15, 'M': 25, 'L': 40, 'XL': 60}.get(size, 25)
    labor_cost = {'S': 30, 'M': 45, 'L': 65, 'XL': 90}.get(size, 45)
    subtotal_before_delivery = flower_cost + packaging_cost + labor_cost
    delivery_fee = 20 if subtotal_before_delivery < 200 else 0
    total_price = subtotal_before_delivery + delivery_fee
    return {
        "flower_cost": flower_cost,
        "packaging_cost": packaging_cost,
        "labor_cost": labor_cost,
        "delivery_fee": delivery_fee,
        "subtotal_before_delivery": subtotal_before_delivery,
        "total_price": total_price,
        "flower_detail": flower_detail
    }


# ========== 初始化session_state ==========
if "recommend_result" not in st.session_state:
    st.session_state.recommend_result = None
if "selected_flowers" not in st.session_state:
    st.session_state.selected_flowers = []
if "bouquet_desc" not in st.session_state:
    st.session_state.bouquet_desc = None
if "history" not in st.session_state:
    st.session_state.history = []
if "target" not in st.session_state:
    st.session_state.target = "恋人"
if "occasion" not in st.session_state:
    st.session_state.occasion = "日常惊喜"
if "color" not in st.session_state:
    st.session_state.color = "粉色"
if "style" not in st.session_state:
    st.session_state.style = "浪漫"
if "budget" not in st.session_state:
    st.session_state.budget = "中"
if "custom_message" not in st.session_state:
    st.session_state.custom_message = ""
if "size" not in st.session_state:
    st.session_state.size = "M"
if "flower_quantities" not in st.session_state:
    st.session_state.flower_quantities = {}


# ========== 头部 ==========
st.markdown("""
<div class="main-header">
    <div style="font-size: 60px; margin-bottom: 10px;">💐</div>
    <h1 style="font-size: 42px; margin: 0;">AI花束定制平台</h1>
    <p style="font-size: 16px; opacity: 0.9; margin-top: 10px;">智能花艺推荐 · 专属花束设计 · 线下花店配送</p>
    <p style="font-size: 12px; opacity: 0.7; margin-top: 5px;">🤖 Powered by ECNU Chat 大语言模型 | 第三届全民数字素养与AI创新应用大赛</p>
</div>
""", unsafe_allow_html=True)

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown("### 🌸 定制你的花束")
    st.markdown("---")
    st.markdown("### ⚡ 快速搭配")
    quick_options = {
        "🌹 经典浪漫": {"target": "恋人", "occasion": "情人节", "color": "红色", "style": "浪漫"},
        "🌸 母亲节暖心": {"target": "家人", "occasion": "母亲节", "color": "粉色", "style": "温馨"},
        "🍃 清新文艺": {"target": "朋友", "occasion": "生日", "color": "白色", "style": "清新自然"},
        "🌻 阳光活力": {"target": "朋友", "occasion": "毕业", "color": "黄色", "style": "阳光活力"},
    }
    quick_col1, quick_col2 = st.columns(2)
    quick_items = list(quick_options.items())
    for i, (label, config) in enumerate(quick_items):
        col = quick_col1 if i % 2 == 0 else quick_col2
        with col:
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                st.session_state.target = config["target"]
                st.session_state.occasion = config["occasion"]
                st.session_state.color = config["color"]
                st.session_state.style = config["style"]
                st.rerun()
    st.markdown("---")
    target = st.selectbox("👤 送给谁？", ["恋人", "家人", "朋友", "老师", "自己", "客户", "孩子"])
    st.session_state.target = target
    occasion = st.selectbox("🎉 什么场合？", ["日常惊喜", "生日", "表白", "纪念日", "毕业", "情人节", "乔迁", "开业", "探望", "道歉", "婚礼", "年节", "母亲节"])
    st.session_state.occasion = occasion
    st.markdown("---")
    st.session_state.color = st.selectbox("🎨 偏好颜色", ["任意", "粉色", "红色", "白色", "紫色", "黄色", "橙色", "蓝色", "绿色"])
    st.session_state.style = st.selectbox("✨ 偏好风格", ["任意", "浪漫", "清新自然", "简约高级", "阳光活力", "复古", "可爱", "华丽大气", "温馨"])
    st.session_state.budget = st.selectbox("💰 预算", ["任意", "低", "中", "中高", "高"])
    # 尺寸选择
    size_options = {
        "S": "🌱 S码 - 小巧精致 (3-5支主花)",
        "M": "💐 M码 - 标准适中 (5-8支主花)",
        "L": "🌺 L码 - 大气饱满 (8-12支主花)",
        "XL": "🎊 XL码 - 豪华盛宴 (12-18支主花)"
    }
    st.session_state.size = st.selectbox("📏 花束尺寸", list(size_options.keys()), format_func=lambda x: size_options[x])
    st.markdown("---")
    st.caption("🤖 由 ChatECNU 大模型驱动")
    st.caption("🏪 合作花店: 华东师大周边花店")
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 📜 历史搭配")
        for i, record in enumerate(st.session_state.history[:5]):
            if st.button(f"💐 {record['time']} · {', '.join(record['flowers'][:2])}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_flowers = record.get("selected_flowers", [])
                st.rerun()

# ========== 主区域 ==========

# 灵感画廊
st.markdown("### 🖼️ 灵感画廊")
st.markdown("*点击下方按钮，一键套用风格*")
gallery_data = [
    ("🌹", "红玫瑰恋曲", "经典浪漫", {"target": "恋人", "occasion": "情人节", "color": "红色", "style": "浪漫"}),
    ("🌻", "向日葵阳光", "清新活力", {"target": "朋友", "occasion": "毕业", "color": "黄色", "style": "阳光活力"}),
    ("🤍", "纯白新娘", "简约高级", {"target": "恋人", "occasion": "婚礼", "color": "白色", "style": "简约高级"}),
    ("💜", "紫色梦境", "神秘优雅", {"target": "恋人", "occasion": "纪念日", "color": "紫色", "style": "浪漫"}),
]
gallery_cols = st.columns(4)
for i, (emoji, name, tag, config) in enumerate(gallery_data):
    with gallery_cols[i]:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #fff, #fef5f7); border-radius: 16px; padding: 15px; text-align: center; border: 1px solid #eee; margin-bottom: 8px;"><div style="font-size: 36px;">{emoji}</div><div style="font-weight: bold; font-size: 14px;">{name}</div><span class="price-tag" style="font-size: 10px; display: inline-block; margin-top: 6px;">{tag}</span></div>""", unsafe_allow_html=True)
        if st.button(f"✨ 试试这个", key=f"gallery_{i}", use_container_width=True):
            st.session_state.target = config["target"]
            st.session_state.occasion = config["occasion"]
            st.session_state.color = config["color"]
            st.session_state.style = config["style"]
            st.rerun()

st.markdown("---")

# AI推荐按钮
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("✨ AI智能推荐花材", use_container_width=True):
        with st.spinner("💐 AI花艺师正在为您精心搭配..."):
            result = recommend_flowers_balanced(
                target=st.session_state.target,
                occasion=st.session_state.occasion,
                color_preference=st.session_state.color if st.session_state.color != "任意" else "",
                style=st.session_state.style if st.session_state.style != "任意" else "浪漫",
                budget=st.session_state.budget if st.session_state.budget != "任意" else ""
            )
            if result["success"]:
                st.session_state.recommend_result = result
                st.session_state.selected_flowers = result["flowers"]
                st.session_state.flower_quantities = {}
                for flower in st.session_state.selected_flowers:
                    st.session_state.flower_quantities[flower["id"]] = get_default_quantity(flower, st.session_state.size)
                st.success("✅ 推荐完成！")
                st.balloons()
            else:
                st.error("推荐失败")

st.markdown("---")

# 显示推荐结果
if st.session_state.recommend_result:
    result = st.session_state.recommend_result
    st.markdown("### 💌 AI花艺师的温馨推荐")
    st.markdown(f"""<div class="ai-message"><p>💐 {result['recommendation']}</p></div>""", unsafe_allow_html=True)
    
    st.markdown("### 🌷 为您精选的花材")
    st.markdown("*系统已按主花、配花、叶材、果材为您搭配，可调整支数*")
    
    # 按类别分组显示
    main_list = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "主花"]
    filler_list = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "配花"]
    leaf_list = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "叶材"]
    fruit_list = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "果材"]
    
    # 显示主花
    if main_list:
        st.markdown("#### 🌹 主花（花束焦点）")
        cols = st.columns(min(len(main_list), 3))
        for idx, flower in enumerate(main_list):
            with cols[idx % 3]:
                unit_price = flower.get("unit_price", 5)
                st.markdown(f"""<div class="flower-item"><div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div><div class="flower-name">{flower['name']}</div><div class="flower-language">「{flower['language'][:15]}」</div><div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div></div>""", unsafe_allow_html=True)
    
    # 显示配花
    if filler_list:
        st.markdown("#### ✨ 配花（增添层次）")
        cols = st.columns(min(len(filler_list), 3))
        for idx, flower in enumerate(filler_list):
            with cols[idx % 3]:
                unit_price = flower.get("unit_price", 5)
                st.markdown(f"""<div class="flower-item"><div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div><div class="flower-name">{flower['name']}</div><div class="flower-language">「{flower['language'][:15]}」</div><div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div></div>""", unsafe_allow_html=True)
    
    # 显示叶材
    if leaf_list:
        st.markdown("#### 🍃 叶材（自然基底）")
        cols = st.columns(min(len(leaf_list), 3))
        for idx, flower in enumerate(leaf_list):
            with cols[idx % 3]:
                unit_price = flower.get("unit_price", 5)
                st.markdown(f"""<div class="flower-item"><div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div><div class="flower-name">{flower['name']}</div><div class="flower-language">「{flower['language'][:15]}」</div><div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div></div>""", unsafe_allow_html=True)
    
    # 显示果材
    if fruit_list:
        st.markdown("#### 🍎 果材（点睛之笔）")
        cols = st.columns(min(len(fruit_list), 3))
        for idx, flower in enumerate(fruit_list):
            with cols[idx % 3]:
                unit_price = flower.get("unit_price", 5)
                st.markdown(f"""<div class="flower-item"><div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div><div class="flower-name">{flower['name']}</div><div class="flower-language">「{flower['language'][:15]}」</div><div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div></div>""", unsafe_allow_html=True)

# ===== 我的花篮（支数调整） =====
if st.session_state.selected_flowers:
    st.markdown("---")
    st.markdown("### 🛒 我的花篮")
    st.markdown(f"*已选择 {len(st.session_state.selected_flowers)} 种花材 · 尺寸：{st.session_state.size}码*")
    st.caption("💡 提示：可调整每种花材的支数，系统将按实际数量生成AI提示词")
    
    # 分类统计
    main_flowers = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "主花"]
    filler_flowers = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "配花"]
    leaf_flowers = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "叶材"]
    fruit_flowers = [f for f in st.session_state.selected_flowers if get_flower_category(f) == "果材"]
    
    col_main, col_filler, col_leaf, col_fruit = st.columns(4)
    with col_main:
        st.markdown(f"🌹 **主花**：{len(main_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in main_flowers])}支")
    with col_filler:
        st.markdown(f"✨ **配花**：{len(filler_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in filler_flowers])}支")
    with col_leaf:
        st.markdown(f"🍃 **叶材**：{len(leaf_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in leaf_flowers])}支")
    with col_fruit:
        st.markdown(f"🍎 **果材**：{len(fruit_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in fruit_flowers])}支")
    
    # 显示每种花材并允许调整支数
    for i, flower in enumerate(st.session_state.selected_flowers):
        col_a, col_b, col_c, col_d = st.columns([1, 2, 2, 1])
        category = get_flower_category(flower)
        category_emoji = get_category_emoji(category)
        
        with col_a:
            st.write(f"**#{i+1}**")
        with col_b:
            st.write(f"{category_emoji} {flower['name']} ({category})")
        with col_c:
            current_qty = st.session_state.flower_quantities.get(flower["id"], get_default_quantity(flower, st.session_state.size))
            new_qty = st.number_input(
                "支数",
                min_value=get_min_quantity(flower, st.session_state.size),
                max_value=get_max_quantity(flower, st.session_state.size),
                value=current_qty,
                step=get_step(flower),
                key=f"qty_{flower['id']}",
                label_visibility="collapsed"
            )
            st.session_state.flower_quantities[flower["id"]] = new_qty
        with col_d:
            unit_price = flower.get("unit_price", 5)
            st.write(f"¥{unit_price}/支 → **¥{new_qty * unit_price}**")
    
    # 价格明细
    st.markdown("---")
    st.markdown("### 💰 价格明细")
    price_breakdown = calculate_bouquet_price(st.session_state.selected_flowers, st.session_state.flower_quantities, st.session_state.size)
    
    col_price1, col_price2 = st.columns(2)
    with col_price1:
        st.markdown("**🌷 花材费用明细：**")
        for item in price_breakdown["flower_detail"]:
            if item["quantity"] > 0:
                flower_emoji = get_flower_emoji(item["name"])
                st.write(f"{flower_emoji} {item['name']} ({item['type']}) × {item['quantity']}支 = ¥{item['subtotal']}")
        st.write(f"**花材小计：¥{price_breakdown['flower_cost']}**")
    with col_price2:
        st.markdown("**📦 其他费用：**")
        st.write(f"📦 包装材料费：¥{price_breakdown['packaging_cost']}")
        st.write(f"👨‍🎨 花艺师手工费：¥{price_breakdown['labor_cost']}")
        if price_breakdown['delivery_fee'] > 0:
            st.write(f"🚗 配送费：¥{price_breakdown['delivery_fee']}")
        else:
            st.write("🚗 配送费：**免费** (满¥200免配送费)")
        st.markdown("---")
        st.metric("💰 订单总价", f"¥{price_breakdown['total_price']}")
        st.caption("⚠️ 此为预估价格，最终价格以花艺师确认为准")
    
    # 搭配比例分析
    st.markdown("### 📊 搭配比例分析")
    total_stems = sum(st.session_state.flower_quantities.values())
    main_stems = sum([st.session_state.flower_quantities.get(f['id'], 0) for f in main_flowers])
    filler_stems = sum([st.session_state.flower_quantities.get(f['id'], 0) for f in filler_flowers])
    leaf_stems = sum([st.session_state.flower_quantities.get(f['id'], 0) for f in leaf_flowers])
    
    if total_stems > 0:
        st.progress(main_stems/total_stems, text=f"🌹 主花 {main_stems}支 ({main_stems/total_stems*100:.0f}%)")
        st.progress(filler_stems/total_stems, text=f"✨ 配花 {filler_stems}支 ({filler_stems/total_stems*100:.0f}%)")
        st.progress(leaf_stems/total_stems, text=f"🍃 叶材 {leaf_stems}支 ({leaf_stems/total_stems*100:.0f}%)")
        
        if main_stems == 0:
            st.warning("💡 请至少设置1种主花，让花束有视觉焦点")
        elif main_stems/total_stems < 0.2:
            st.warning("💡 建议主花占比不低于20%，让花束更有焦点")
        elif 0.3 <= main_stems/total_stems <= 0.6:
            st.success("✅ 主配花比例协调，花束层次丰富！")
    
    # 生成花束示意图按钮
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🎨 生成花束示意图", type="primary", use_container_width=True):
            with st.spinner("🎨 AI正在构思花束设计..."):
                desc_result = generate_bouquet_description_with_details(
                    flower_quantities=st.session_state.flower_quantities,
                    selected_flowers=st.session_state.selected_flowers,
                    color_preference=st.session_state.color if st.session_state.color != "任意" else "",
                    style=st.session_state.style if st.session_state.style != "任意" else "浪漫"
                )
                if desc_result["success"]:
                    st.session_state.bouquet_desc = desc_result["description"]
                    st.success("✨ 花束描述生成成功！")
                    st.rerun()
                else:
                    st.error(desc_result.get("message", "生成失败"))
    with col_btn2:
        if total_stems > 0:
            st.metric("🌸 总花材支数", f"{total_stems}支")

# ===== 花束示意图展示区 =====
if st.session_state.bouquet_desc:
    st.markdown("---")
    st.markdown("### 🖼️ AI花束示意图")
    st.info("💡 **提示**：示意图仅展示花材搭配风格和配色，最终成品以花艺师制作为准")
    
    with st.expander("📝 查看AI生图提示词", expanded=True):
        st.code(st.session_state.bouquet_desc, language="text")
        st.caption("💡 提示词已包含：每种花材的具体数量、整体色调、花束形状、包装风格")
    
    st.markdown("### 💌 定制祝福语")
    st.session_state.custom_message = st.text_area("写下你想对Ta说的话...", value=st.session_state.custom_message, height=80)
    
    if st.session_state.selected_flowers:
        flower_categories = [f"「{f['name']}」({get_flower_category(f)})" for f in st.session_state.selected_flowers[:5]]
        if st.session_state.custom_message:
            st.info(f"💐 {st.session_state.custom_message}\n\n🌸 " + " + ".join(flower_categories))
        else:
            st.info("🌸 " + " + ".join(flower_categories))
    
    # 订单按钮
    st.markdown("---")
    if st.session_state.selected_flowers:
        price_breakdown = calculate_bouquet_price(st.session_state.selected_flowers, st.session_state.flower_quantities, st.session_state.size)
        
        col_order1, col_order2, col_order3 = st.columns([1, 2, 1])
        with col_order2:
            if st.button("💐 确认订单，配送到家", type="primary", use_container_width=True):
                new_record = {
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "flowers": [f["name"] for f in st.session_state.selected_flowers],
                    "selected_flowers": st.session_state.selected_flowers.copy(),
                }
                if new_record not in st.session_state.history:
                    st.session_state.history.insert(0, new_record)
                    st.session_state.history = st.session_state.history[:10]
                
                st.success("✅ 订单已提交！合作花店将尽快与您联系 📞")
                st.balloons()
                order_details = [f"{item['name']}({item['type']}) × {item['quantity']}支" for item in price_breakdown["flower_detail"] if item["quantity"] > 0]
                st.markdown(f"""### 📋 订单信息
- **花束尺寸**：{st.session_state.size}码
- **花材清单**：{'、'.join(order_details)}
- **总花材数量**：{sum(st.session_state.flower_quantities.values())}支
- **花材费用**：¥{price_breakdown['flower_cost']}
- **包装材料**：¥{price_breakdown['packaging_cost']}
- **手工费**：¥{price_breakdown['labor_cost']}
- **配送费**：{'免费' if price_breakdown['delivery_fee'] == 0 else f"¥{price_breakdown['delivery_fee']}"}
- **订单总价**：**¥{price_breakdown['total_price']}**
- **您的寄语**：{st.session_state.custom_message if st.session_state.custom_message else '无'}
""")
                st.info("💡 工作人员将在30分钟内电话确认订单详情")

# ========== 页脚 ==========
st.markdown("""
<div class="footer">
    <p>© 2026 华东师范大学 · AI花束定制平台</p>
    <p>Powered by ChatECNU 大模型 | 第三届全民数字素养与人工智能创新应用大赛</p>
</div>
""", unsafe_allow_html=True)
