"""
AI花束定制平台 - 完整合并版（Streamlit Cloud可部署）
保留所有原功能：花材推荐、花束描述生成、学校LLM API调用、订单系统
新增：花束尺寸S/M/L/XL、按支数计价、材料费/人工费、用户自定义主花/配花
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
    # 在 API配置 部分后面添加
st.sidebar.write(f"🔍 API_BASE: {API_BASE}")
st.sidebar.write(f"🔍 API_KEY已配置: {'✅是' if API_KEY and API_KEY != '你的API密钥' else '❌否'}")
st.sidebar.write(f"🔍 MODEL: {MODEL_NAME}")
    
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
            self.flower_data = self._get_default_flowers()
    
    def _get_default_flowers(self):
        return [
            {"id": 1, "name": "玫瑰", "color": "红色、粉色、白色、黄色", "language": "爱情、热恋、你是我的唯一", "occasion": ["情人节", "表白", "纪念日", "婚礼"], "target": ["恋人"], "style": "浪漫", "price_level": "中", "unit_price": 8, "category": "主花", "season": "全年", "description": "经典爱情之花，多层花瓣优雅绽放", "scent": "有香味"},
            {"id": 2, "name": "向日葵", "color": "黄色", "language": "沉默的爱、阳光、积极向上", "occasion": ["毕业", "日常惊喜", "探望"], "target": ["朋友", "家人"], "style": "阳光活力", "price_level": "低", "unit_price": 5, "category": "主花", "season": "夏季", "description": "明亮耀眼的大花盘，象征阳光与希望", "scent": "无香味"},
            {"id": 3, "name": "百合", "color": "白色、粉色", "language": "纯洁、优雅、百年好合", "occasion": ["婚礼", "乔迁", "探望"], "target": ["恋人", "家人"], "style": "清新自然", "price_level": "中高", "unit_price": 12, "category": "主花", "season": "全年", "description": "清香四溢的优雅花材，花型优美", "scent": "有香味"},
            {"id": 4, "name": "康乃馨", "color": "粉色、红色、白色", "language": "母爱、温馨、感恩", "occasion": ["母亲节", "探望", "生日"], "target": ["家人", "老师"], "style": "温馨", "price_level": "低", "unit_price": 3, "category": "配花", "season": "全年", "description": "母亲节的代表花卉，温柔而持久", "scent": "有香味"},
            {"id": 5, "name": "满天星", "color": "白色、粉色", "language": "真心喜欢、默默守护", "occasion": ["日常惊喜", "表白", "毕业"], "target": ["恋人", "朋友"], "style": "清新自然", "price_level": "低", "unit_price": 2, "category": "配花", "season": "全年", "description": "星星点点的可爱小花，花束中的精灵", "scent": "无香味"},
            {"id": 6, "name": "郁金香", "color": "红色、黄色、紫色、白色", "language": "爱的宣言、高贵、幸福", "occasion": ["表白", "纪念日", "日常惊喜"], "target": ["恋人"], "style": "简约高级", "price_level": "中高", "unit_price": 10, "category": "主花", "season": "春季", "description": "优雅的杯状花型，荷兰国花", "scent": "无香味"},
            {"id": 7, "name": "绣球", "color": "蓝色、粉色、紫色、白色", "language": "永恒团圆、希望、美满", "occasion": ["乔迁", "婚礼", "探望"], "target": ["家人", "朋友"], "style": "浪漫", "price_level": "中", "unit_price": 15, "category": "主花", "season": "夏季", "description": "圆润饱满的花球，象征团圆美满", "scent": "无香味"},
            {"id": 8, "name": "洋桔梗", "color": "白色、粉色、紫色", "language": "真诚不变的爱、感动", "occasion": ["表白", "生日", "日常惊喜"], "target": ["恋人", "朋友"], "style": "清新自然", "price_level": "中", "unit_price": 6, "category": "主花", "season": "全年", "description": "层层叠叠的花瓣，温柔而雅致", "scent": "无香味"},
            {"id": 9, "name": "尤加利叶", "color": "绿色", "language": "恩赐、回忆、自然", "occasion": ["日常惊喜", "乔迁"], "target": ["朋友", "家人"], "style": "清新自然", "price_level": "低", "unit_price": 3, "category": "配花", "season": "全年", "description": "清新芬芳的叶材，北欧风格代表", "scent": "有香味"},
            {"id": 10, "name": "小雏菊", "color": "白色、黄色", "language": "快乐、天真、隐藏的爱", "occasion": ["毕业", "生日", "日常惊喜"], "target": ["朋友", "孩子"], "style": "可爱", "price_level": "低", "unit_price": 2, "category": "配花", "season": "春季", "description": "小巧可爱的花朵，充满童真", "scent": "无香味"},
            {"id": 11, "name": "牡丹", "color": "粉色、红色、白色", "language": "富贵、圆满、国色天香", "occasion": ["乔迁", "开业", "年节"], "target": ["家人", "客户"], "style": "华丽大气", "price_level": "高", "unit_price": 20, "category": "主花", "season": "春季", "description": "花中之王，大气华贵", "scent": "有香味"},
            {"id": 12, "name": "勿忘我", "color": "紫色、蓝色", "language": "永恒的记忆、真爱", "occasion": ["纪念日", "毕业", "表白"], "target": ["恋人", "朋友"], "style": "清新自然", "price_level": "低", "unit_price": 2, "category": "配花", "season": "全年", "description": "小巧的紫色花朵，可做干花", "scent": "无香味"},
            {"id": 13, "name": "泡泡玫瑰", "color": "粉色、白色、橙色", "language": "多变的爱、小巧可人", "occasion": ["日常惊喜", "生日", "表白"], "target": ["恋人", "朋友"], "style": "可爱", "price_level": "中", "unit_price": 6, "category": "主花", "season": "全年", "description": "多头小玫瑰，可爱又浪漫", "scent": "有香味"}
        ]
    
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


rag_engine = FlowerRAGEngine()


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
        st.warning(f"⚠️ LLM调用失败，将使用备用推荐语")
        return None


# ========== 业务函数 ==========
def recommend_flowers(target, occasion, color_preference, style, budget, flower_type="", season="", has_scent=""):
    query = f"{target} {occasion} {color_preference} {style} {budget}"
    rag_results = rag_engine.search(query, top_k=6)
    filtered_results = rag_results
    if flower_type:
        filtered_results = [f for f in filtered_results if get_flower_type(f['name']) == flower_type]
    if season and season != "全年":
        filtered_results = [f for f in filtered_results if f.get('season', '全年') == season or f.get('season', '全年') == '全年']
    if has_scent == "有香味":
        filtered_results = [f for f in filtered_results if f.get('scent', '') == '有香味']
    elif has_scent == "无香味":
        filtered_results = [f for f in filtered_results if f.get('scent', '') == '无香味']
    if not filtered_results:
        filtered_results = rag_results[:4]
    prompt = f"""你是一个专业的花艺推荐师。请根据以下花材推荐结果，写一段150字以内的推荐语。
推荐对象：{target}
场合：{occasion}
颜色偏好：{color_preference}
风格偏好：{style}
推荐花材列表：
{json.dumps(filtered_results, ensure_ascii=False, indent=2)}
请输出一段温暖有感染力的推荐语。"""
    recommendation_text = call_ecnu_llm("你是一位温暖专业的花艺推荐师。", prompt)
    if not recommendation_text:
        flower_names = "、".join([f["name"] for f in filtered_results[:4]])
        recommendation_text = f"🌷 为您精心推荐了以下花材！结合「{target}」的身份和「{occasion}」的场合，{flower_names}等花材在花语寓意和风格上都很契合。您可以从中挑选喜欢的花材，自由搭配出专属花束～"
    return {"success": True, "flowers": filtered_results, "recommendation": recommendation_text}


def generate_bouquet_description(flower_ids, color_preference=""):
    selected_flowers = [f for f in rag_engine.flower_data if f["id"] in flower_ids]
    flower_names = [f["name"] for f in selected_flowers]
    if not flower_names:
        return {"success": False, "message": "请至少选择一种花材"}
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
        color_keywords = "、".join(flower_colors[:3])
    else:
        color_keywords = "vibrant"
    prompt = f"""请将以下花材组合转化为一段英文的花束描述，用于AI文生图工具生成花束图片。
花材：{'、'.join(flower_names)}
整体色彩：{color_keywords}
要求：
- 描述中必须包含「{color_keywords}」作为整体色调
- 描述花材的层次、包装风格
- 包含 "bouquet"、"wrapped in kraft paper"、"floral photography" 等关键词
- 用词优美，适合AI绘画
- 输出纯英文，60词以内
- 示例格式："A beautiful {color_keywords} bouquet of roses and lilies, wrapped in kraft paper..."
"""
    description = call_ecnu_llm("你擅长将花材搭配转化为优美的英文描述，注意突出整体色调。", prompt, max_tokens=200)
    if not description:
        flower_names_str = " and ".join(flower_names[:3])
        description = f"A stunning {color_keywords} bouquet of {flower_names_str}, fresh floral arrangement with layered textures, soft natural lighting, wrapped in kraft paper, professional floral photography style, high quality, 8k."
    return {"success": True, "description": description, "flower_names": flower_names, "color_theme": color_preference or "自然搭配"}


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


def get_flower_type(flower_name):
    # 优先使用用户自定义的分类
    if "custom_types" in st.session_state and flower_name in st.session_state.custom_types:
        return st.session_state.custom_types[flower_name]
    
    # 从数据库获取默认分类
    for flower in rag_engine.flower_data:
        if flower['name'] == flower_name:
            category = flower.get('category', '配花')
            if category in ['叶材', '果材']:
                return '配花'
            return category
    
    # 原有逻辑作为后备
    leaf_keywords = ['叶', '草', '蕨', '松', '竹', '尤加利', '喷泉', '龟背', '散尾', '蓬莱', '排草', '羊齿', '剑叶', '栀子叶', '龙柳', '红瑞木']
    filler_keywords = ['满天星', '勿忘我', '情人草', '水晶草', '蕾丝', '翠珠', '风铃', '蓝星', '松虫', '鼠尾', '相思梅', '翠菊', '波斯菊', '黄金球', '澳洲米花']
    fruit_keywords = ['红豆', '冬青', '火棘', '灯笼果', '蔷薇果', '棉花', '蒲棒', '芦苇']
    name_lower = flower_name.lower()
    if any(kw in name_lower for kw in leaf_keywords):
        return '叶材'
    elif any(kw in name_lower for kw in filler_keywords):
        return '配花'
    elif any(kw in name_lower for kw in fruit_keywords):
        return '果材'
    else:
        return '主花'


def get_default_quantity(flower, size):
    flower_type = get_flower_type(flower['name'])
    size_defaults = {
        'S': {'主花': 3, '配花': 2},
        'M': {'主花': 5, '配花': 3},
        'L': {'主花': 8, '配花': 5},
        'XL': {'主花': 12, '配花': 8}
    }
    return size_defaults.get(size, {}).get(flower_type, 3)


def get_min_quantity(flower, size):
    return 1


def get_max_quantity(flower, size):
    flower_type = get_flower_type(flower['name'])
    size_max = {'S': 5, 'M': 10, 'L': 20, 'XL': 30}
    type_max = {'主花': size_max.get(size, 10), '配花': size_max.get(size, 10) * 2}
    return type_max.get(flower_type, 10)


def get_step(flower):
    flower_type = get_flower_type(flower['name'])
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
            "type": get_flower_type(flower['name']),
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
if "flower_type_filter" not in st.session_state:
    st.session_state.flower_type_filter = "全部"
if "season_filter" not in st.session_state:
    st.session_state.season_filter = "全年"
if "has_scent_filter" not in st.session_state:
    st.session_state.has_scent_filter = "全部"
if "custom_message" not in st.session_state:
    st.session_state.custom_message = ""
if "size" not in st.session_state:
    st.session_state.size = "M"
if "flower_quantities" not in st.session_state:
    st.session_state.flower_quantities = {}
# 新增：用户自定义花材分类
if "custom_types" not in st.session_state:
    st.session_state.custom_types = {}


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
    with st.expander("🎯 高级筛选（花材类型/季节/香味）", expanded=False):
        st.session_state.flower_type_filter = st.selectbox("🌿 花材类型", ["全部", "主花", "配花", "叶材", "果材"])
        st.session_state.season_filter = st.selectbox("📅 适用季节", ["全年", "春季", "夏季", "秋季", "冬季"])
        st.session_state.has_scent_filter = st.selectbox("🌺 香气", ["全部", "有香味", "无香味"])
    st.markdown("---")
    st.session_state.color = st.selectbox("🎨 偏好颜色", ["任意", "粉色", "红色", "白色", "紫色", "黄色", "橙色", "蓝色", "绿色"])
    st.session_state.style = st.selectbox("✨ 偏好风格", ["任意", "浪漫", "清新自然", "简约高级", "阳光活力", "复古", "可爱", "华丽大气"])
    st.session_state.budget = st.selectbox("💰 预算", ["任意", "低", "中", "中高", "高"])
    # 尺寸选择
    size_options = {
        "S": "🌱 S码 - 小巧精致",
        "M": "💐 M码 - 标准适中",
        "L": "🌺 L码 - 大气饱满",
        "XL": "🎊 XL码 - 豪华盛宴"
    }
    st.session_state.size = st.selectbox("📏 花束尺寸", list(size_options.keys()), format_func=lambda x: size_options[x], help="S：10-15cm | M：20-25cm | L：30-35cm | XL：40cm+")
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
        with st.spinner("💐 AI花艺师正在精心搭配..."):
            result = recommend_flowers(
                target=st.session_state.target,
                occasion=st.session_state.occasion,
                color_preference=st.session_state.color if st.session_state.color != "任意" else "",
                style=st.session_state.style if st.session_state.style != "任意" else "",
                budget=st.session_state.budget if st.session_state.budget != "任意" else "",
                flower_type=st.session_state.flower_type_filter if st.session_state.flower_type_filter != "全部" else "",
                season=st.session_state.season_filter if st.session_state.season_filter != "全年" else "",
                has_scent=st.session_state.has_scent_filter if st.session_state.has_scent_filter != "全部" else ""
            )
            if result["success"]:
                st.session_state.recommend_result = result
                st.session_state.selected_flowers = []
                st.session_state.flower_quantities = {}
                st.session_state.custom_types = {}
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
    st.markdown("*点击花材卡片即可选择，支持多选搭配*")
    cols = st.columns(2)
    for idx, flower in enumerate(result["flowers"]):
        with cols[idx % 2]:
            is_selected = any(f["id"] == flower["id"] for f in st.session_state.selected_flowers)
            unit_price = flower.get("unit_price", 5)
            st.markdown(f"""<div class="flower-item" style="border: 2px solid {'#ff6b9d' if is_selected else '#eee'};"><div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div><div class="flower-name">{flower['name']}</div><div class="flower-language">「{flower['language']}」</div><div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span><span style="margin-left: 8px; font-size: 11px;">🎨 {flower['color']}</span></div></div>""", unsafe_allow_html=True)
            if is_selected:
                if st.button(f"✅ 已选", key=f"remove_{flower['id']}", use_container_width=True):
                    st.session_state.selected_flowers = [f for f in st.session_state.selected_flowers if f["id"] != flower["id"]]
                    if flower["id"] in st.session_state.flower_quantities:
                        del st.session_state.flower_quantities[flower["id"]]
                    if flower["name"] in st.session_state.custom_types:
                        del st.session_state.custom_types[flower["name"]]
                    st.rerun()
            else:
                if st.button(f"🌸 选择", key=f"select_{flower['id']}", use_container_width=True):
                    st.session_state.selected_flowers.append(flower)
                    st.rerun()

    # 我的花篮（新增自定义分类切换）
    if st.session_state.selected_flowers:
        st.markdown("---")
        st.markdown("### 🛒 我的花篮")
        st.markdown(f"*已选择 {len(st.session_state.selected_flowers)} 种花材 · 尺寸：{st.session_state.size}码*")
        st.caption("💡 提示：可调整支数、上下移动顺序、点击「切换」改变主花/配花分类")

        # 初始化默认支数和分类
        for flower in st.session_state.selected_flowers:
            if flower["id"] not in st.session_state.flower_quantities:
                st.session_state.flower_quantities[flower["id"]] = get_default_quantity(flower, st.session_state.size)
            if flower["name"] not in st.session_state.custom_types:
                # 使用数据库默认分类（叶材果材已归入配花）
                default_category = flower.get("category", "配花")
                if default_category in ["叶材", "果材"]:
                    default_category = "配花"
                st.session_state.custom_types[flower["name"]] = default_category

        # 分类统计
        main_flowers = [f for f in st.session_state.selected_flowers if st.session_state.custom_types.get(f["name"], "配花") == "主花"]
        filler_flowers = [f for f in st.session_state.selected_flowers if st.session_state.custom_types.get(f["name"], "配花") == "配花"]
        
        col_main, col_filler = st.columns(2)
        with col_main:
            st.markdown(f"🌹 **主花**：{len(main_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in main_flowers])}支")
        with col_filler:
            st.markdown(f"✨ **配花**：{len(filler_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in filler_flowers])}支")

        # 显示每种花材
        for i, flower in enumerate(st.session_state.selected_flowers):
            col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns([0.3, 1.5, 1.5, 1, 0.8, 0.3, 0.3])
            
            with col_a:
                st.write(f"**#{i+1}**")
            with col_b:
                st.write(f"{get_flower_emoji(flower['name'])} {flower['name']}")
            with col_c:
                current_type = st.session_state.custom_types.get(flower["name"], "配花")
                type_emoji = "🌹" if current_type == "主花" else "✨"
                unit_price = flower.get("unit_price", 5)
                st.write(f"{type_emoji} {current_type} | ¥{unit_price}/支")
            with col_d:
                new_qty = st.number_input(
                    "支数",
                    min_value=get_min_quantity(flower, st.session_state.size),
                    max_value=get_max_quantity(flower, st.session_state.size),
                    value=st.session_state.flower_quantities.get(flower["id"], get_default_quantity(flower, st.session_state.size)),
                    step=get_step(flower),
                    key=f"qty_{flower['id']}"
                )
                st.session_state.flower_quantities[flower["id"]] = new_qty
            with col_e:
                # 切换主花/配花按钮
                current_type = st.session_state.custom_types.get(flower["name"], "配花")
                if current_type == "主花":
                    if st.button("📌 改配花", key=f"toggle_{flower['id']}", use_container_width=True, help="点击切换为配花"):
                        st.session_state.custom_types[flower["name"]] = "配花"
                        st.rerun()
                else:
                    if st.button("⭐ 改主花", key=f"toggle_{flower['id']}", use_container_width=True, help="点击切换为主花"):
                        st.session_state.custom_types[flower["name"]] = "主花"
                        st.rerun()
            with col_f:
                if i > 0 and st.button("⬆️", key=f"up_{flower['id']}"):
                    new_list = st.session_state.selected_flowers.copy()
                    new_list[i], new_list[i-1] = new_list[i-1], new_list[i]
                    st.session_state.selected_flowers = new_list
                    st.rerun()
            with col_g:
                if i < len(st.session_state.selected_flowers) - 1 and st.button("⬇️", key=f"down_{flower['id']}"):
                    new_list = st.session_state.selected_flowers.copy()
                    new_list[i], new_list[i+1] = new_list[i+1], new_list[i]
                    st.session_state.selected_flowers = new_list
                    st.rerun()

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
        if total_stems > 0:
            st.progress(main_stems/total_stems, text=f"🌹 主花 {main_stems}支 ({main_stems/total_stems*100:.0f}%)")
            st.progress(filler_stems/total_stems, text=f"✨ 配花 {filler_stems}支 ({filler_stems/total_stems*100:.0f}%)")
            if main_stems == 0:
                st.warning("💡 请至少设置1种主花，让花束有视觉焦点")
            elif main_stems/total_stems < 0.2:
                st.warning("💡 建议主花占比不低于20%，让花束更有焦点")
            elif main_stems/total_stems > 0.8:
                st.info("💡 可以适当增加配花，让花束更有层次感")
            elif 0.3 <= main_stems/total_stems <= 0.7:
                st.success("✅ 主配花比例协调，花束层次丰富！")

        # 一键建议分类按钮
        if st.button("🔄 一键建议分类", help="根据花材特性自动建议主花/配花分类"):
            for flower in st.session_state.selected_flowers:
                default_category = flower.get("category", "配花")
                if default_category in ["叶材", "果材"]:
                    default_category = "配花"
                st.session_state.custom_types[flower["name"]] = default_category
            st.success("✅ 已恢复默认分类建议")
            st.rerun()

        # 生成花束示意图按钮
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🎨 生成花束示意图", type="primary", use_container_width=True):
                with st.spinner("🎨 AI正在构思花束设计..."):
                    selected_ids = [f["id"] for f in st.session_state.selected_flowers]
                    desc_result = generate_bouquet_description(
                        flower_ids=selected_ids,
                        color_preference=st.session_state.color if st.session_state.color != "任意" else ""
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
    
    # 花语祝福
    st.markdown("### 💌 定制祝福语")
    st.session_state.custom_message = st.text_area("写下你想对Ta说的话...", value=st.session_state.custom_message, height=80)
    
    if st.session_state.selected_flowers:
        flower_languages = [f"「{f['name']}」：{f['language'][:20]}..." for f in st.session_state.selected_flowers[:5]]
        if st.session_state.custom_message:
            st.info(f"💐 {st.session_state.custom_message}\n\n🌸 " + "\n".join(flower_languages))
        else:
            st.info("🌸 " + "\n".join(flower_languages))
    
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
