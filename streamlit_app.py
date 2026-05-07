"""
AI花束定制平台 - 完整合并版（Streamlit Cloud可部署）
保留所有原功能：花材推荐、花束描述生成、学校LLM API调用
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
# Streamlit Cloud环境变量配置：
# 在Streamlit Cloud的Settings -> Secrets中添加：
# ECNU_API_KEY = "你的学校API密钥"
# ECNU_API_BASE = "https://chat.ecnu.edu.cn/api/v1"
# ECNU_MODEL = "ecnu-chat-model"

# 优先从st.secrets读取（Streamlit Cloud），否则从环境变量读取
try:
    API_KEY = st.secrets.get("ECNU_API_KEY", os.getenv("ECNU_API_KEY", ""))
    API_BASE = st.secrets.get("ECNU_API_BASE", os.getenv("ECNU_API_BASE", "https://chat.ecnu.edu.cn/api/v1"))
    MODEL_NAME = st.secrets.get("ECNU_MODEL", os.getenv("ECNU_MODEL", "ecnu-chat-model"))
except:
    API_KEY = os.getenv("ECNU_API_KEY", "")
    API_BASE = os.getenv("ECNU_API_BASE", "https://chat.ecnu.edu.cn/api/v1")
    MODEL_NAME = os.getenv("ECNU_MODEL", "ecnu-chat-model")

# ========== 自定义CSS样式 ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #fff9fb 0%, #fff5f8 100%);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        border-radius: 10px;
    }
    
    .main-header {
        text-align: center;
        padding: 40px 20px 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 0 0 30px 30px;
        margin: -60px -50px 30px -50px;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .flower-item {
        background: linear-gradient(135deg, #fff 0%, #fef5f7 100%);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255,107,157,0.2);
        transition: all 0.3s ease;
        cursor: pointer;
        height: 100%;
    }
    .flower-item:hover {
        transform: translateY(-5px);
        border-color: #ff6b9d;
        box-shadow: 0 10px 25px rgba(255,107,157,0.15);
    }
    
    .flower-visual {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        margin: 0 auto 12px;
        background: conic-gradient(from 0deg, #ff6b9d, #8b5cf6, #667eea, #ff6b9d);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 40px;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    
    .flower-name {
        font-size: 18px;
        font-weight: bold;
        text-align: center;
        color: #333;
        margin-bottom: 6px;
    }
    
    .flower-language {
        font-size: 12px;
        text-align: center;
        color: #ff6b9d;
        margin-bottom: 10px;
        font-style: italic;
    }
    
    @keyframes bouquet-spin {
        0% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(180deg) scale(1.1); }
        100% { transform: rotate(360deg) scale(1); }
    }
    .loading-bouquet {
        animation: bouquet-spin 2s ease-in-out infinite;
        font-size: 60px;
        text-align: center;
        display: inline-block;
    }
    
    .ai-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 20px;
        border-top-left-radius: 5px;
        margin: 20px 0;
        box-shadow: 0 5px 15px rgba(102,126,234,0.3);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        color: white;
        border: none;
        border-radius: 40px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255,107,157,0.4);
    }
    
    .price-tag {
        display: inline-block;
        background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: bold;
    }
    
    .season-tag {
        display: inline-block;
        background: rgba(102,126,234,0.1);
        color: #667eea;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 10px;
        margin-left: 6px;
    }
    
    .footer {
        text-align: center;
        padding: 30px;
        margin-top: 50px;
        color: #999;
        font-size: 12px;
        border-top: 1px solid rgba(255,107,157,0.2);
    }
</style>
""", unsafe_allow_html=True)


# ========== 花语知识检索引擎（原rag_engine.py的内容）==========
class FlowerRAGEngine:
    def __init__(self):
        """初始化RAG引擎，加载知识库"""
        try:
            # 尝试相对路径加载
            knowledge_path = os.path.join(os.path.dirname(__file__), "knowledge_base", "flower_knowledge.json")
            with open(knowledge_path, "r", encoding="utf-8") as f:
                self.flower_data = json.load(f)
        except FileNotFoundError:
            # 如果找不到文件，使用内置数据
            self.flower_data = self._get_default_flowers()
        
        print(f"[RAG] 已加载 {len(self.flower_data)} 种花材，使用关键词匹配模式")
    
    def _get_default_flowers(self):
        """如果找不到知识库文件，使用内置花材数据"""
        return [
            {
                "id": 1, "name": "玫瑰", "color": "红色、粉色、白色、黄色",
                "language": "爱情、热恋、你是我的唯一",
                "occasion": ["情人节", "表白", "纪念日", "婚礼"],
                "target": ["恋人"],
                "style": "浪漫", "price_level": "中", "season": "全年",
                "description": "经典爱情之花，多层花瓣优雅绽放",
                "scent": "有香味"
            },
            {
                "id": 2, "name": "向日葵", "color": "黄色",
                "language": "沉默的爱、阳光、积极向上",
                "occasion": ["毕业", "日常惊喜", "探望"],
                "target": ["朋友", "家人"],
                "style": "阳光活力", "price_level": "低", "season": "夏季",
                "description": "明亮耀眼的大花盘，象征阳光与希望",
                "scent": "无香味"
            },
            {
                "id": 3, "name": "百合", "color": "白色、粉色",
                "language": "纯洁、优雅、百年好合",
                "occasion": ["婚礼", "乔迁", "探望"],
                "target": ["恋人", "家人"],
                "style": "清新自然", "price_level": "中高", "season": "全年",
                "description": "清香四溢的优雅花材，花型优美",
                "scent": "有香味"
            },
            {
                "id": 4, "name": "康乃馨", "color": "粉色、红色、白色",
                "language": "母爱、温馨、感恩",
                "occasion": ["母亲节", "探望", "生日"],
                "target": ["家人", "老师"],
                "style": "温馨", "price_level": "低", "season": "全年",
                "description": "母亲节的代表花卉，温柔而持久",
                "scent": "有香味"
            },
            {
                "id": 5, "name": "满天星", "color": "白色、粉色",
                "language": "真心喜欢、默默守护",
                "occasion": ["日常惊喜", "表白", "毕业"],
                "target": ["恋人", "朋友"],
                "style": "清新自然", "price_level": "低", "season": "全年",
                "description": "星星点点的可爱小花，花束中的精灵",
                "scent": "无香味"
            },
            {
                "id": 6, "name": "郁金香", "color": "红色、黄色、紫色、白色",
                "language": "爱的宣言、高贵、幸福",
                "occasion": ["表白", "纪念日", "日常惊喜"],
                "target": ["恋人"],
                "style": "简约高级", "price_level": "中高", "season": "春季",
                "description": "优雅的杯状花型，荷兰国花",
                "scent": "无香味"
            },
            {
                "id": 7, "name": "绣球", "color": "蓝色、粉色、紫色、白色",
                "language": "永恒团圆、希望、美满",
                "occasion": ["乔迁", "婚礼", "探望"],
                "target": ["家人", "朋友"],
                "style": "浪漫", "price_level": "中", "season": "夏季",
                "description": "圆润饱满的花球，象征团圆美满",
                "scent": "无香味"
            },
            {
                "id": 8, "name": "洋桔梗", "color": "白色、粉色、紫色",
                "language": "真诚不变的爱、感动",
                "occasion": ["表白", "生日", "日常惊喜"],
                "target": ["恋人", "朋友"],
                "style": "清新自然", "price_level": "中", "season": "全年",
                "description": "层层叠叠的花瓣，温柔而雅致",
                "scent": "无香味"
            },
            {
                "id": 9, "name": "尤加利叶", "color": "绿色",
                "language": "恩赐、回忆、自然",
                "occasion": ["日常惊喜", "乔迁"],
                "target": ["朋友", "家人"],
                "style": "清新自然", "price_level": "低", "season": "全年",
                "description": "清新芬芳的叶材，北欧风格代表",
                "scent": "有香味"
            },
            {
                "id": 10, "name": "小雏菊", "color": "白色、黄色",
                "language": "快乐、天真、隐藏的爱",
                "occasion": ["毕业", "生日", "日常惊喜"],
                "target": ["朋友", "孩子"],
                "style": "可爱", "price_level": "低", "season": "春季",
                "description": "小巧可爱的花朵，充满童真",
                "scent": "无香味"
            },
            {
                "id": 11, "name": "牡丹", "color": "粉色、红色、白色",
                "language": "富贵、圆满、国色天香",
                "occasion": ["乔迁", "开业", "年节"],
                "target": ["家人", "客户"],
                "style": "华丽大气", "price_level": "高", "season": "春季",
                "description": "花中之王，大气华贵",
                "scent": "有香味"
            },
            {
                "id": 12, "name": "勿忘我", "color": "紫色、蓝色",
                "language": "永恒的记忆、真爱",
                "occasion": ["纪念日", "毕业", "表白"],
                "target": ["恋人", "朋友"],
                "style": "清新自然", "price_level": "低", "season": "全年",
                "description": "小巧的紫色花朵，可做干花",
                "scent": "无香味"
            }
        ]
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """关键词匹配检索"""
        if not self.flower_data:
            return []
            
        query = query.lower()
        keywords = set(query.replace("、", " ").split())
        
        scored_flowers = []
        for flower in self.flower_data:
            score = 0
            search_text = (
                flower.get("name", "") + flower.get("color", "") + flower.get("language", "") + 
                " ".join(flower.get("occasion", [])) + " ".join(flower.get("target", [])) +
                flower.get("style", "") + flower.get("description", "")
            ).lower()
            
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


# ========== 初始化RAG引擎 ==========
rag_engine = FlowerRAGEngine()


# ========== 学校LLM API调用函数 ==========
def call_ecnu_llm(system_prompt: str, user_prompt: str, max_tokens: int = 300) -> str:
    """
    调用学校大语言模型API
    返回生成的文本，如果调用失败返回None
    """
    if not API_KEY or API_KEY == "你的API密钥":
        st.warning("⚠️ 学校LLM API未配置。请在Streamlit Cloud的Settings -> Secrets中配置ECNU_API_KEY")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        resp = http_requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    
    except http_requests.exceptions.Timeout:
        st.warning("⏱️ 学校API调用超时，将使用备用推荐语")
        return None
    except http_requests.exceptions.ConnectionError:
        st.warning("🔌 无法连接到学校API，请检查网络")
        return None
    except Exception as e:
        st.warning(f"⚠️ LLM调用失败: {str(e)[:100]}，将使用备用推荐语")
        return None


# ========== 花材推荐函数（原/api/recommend）==========
def recommend_flowers(target: str, occasion: str, color_preference: str, 
                     style: str, budget: str, flower_type: str = "", 
                     season: str = "", has_scent: str = "") -> Dict:
    """AI花材推荐"""
    query = f"{target} {occasion} {color_preference} {style} {budget}"
    rag_results = rag_engine.search(query, top_k=6)
    
    # 应用高级筛选
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

    recommendation_text = call_ecnu_llm(
        system_prompt="你是一位温暖专业的花艺推荐师。",
        user_prompt=prompt
    )
    
    if not recommendation_text:
        flower_names = "、".join([f["name"] for f in filtered_results[:4]])
        recommendation_text = f"🌷 为您精心推荐了以下花材！结合「{target}」的身份和「{occasion}」的场合，{flower_names}等花材在花语寓意和风格上都很契合。您可以从中挑选喜欢的花材，自由搭配出专属花束～"
    
    return {
        "success": True,
        "flowers": filtered_results,
        "recommendation": recommendation_text
    }


# ========== 花束描述生成函数（原/api/generate-description）==========
def generate_bouquet_description(flower_ids: List[int], color_preference: str = "") -> Dict:
    """生成花束描述（用于文生图）"""
    selected_flowers = [f for f in rag_engine.flower_data if f["id"] in flower_ids]
    flower_names = [f["name"] for f in selected_flowers]
    
    if not flower_names:
        return {
            "success": False,
            "message": "请至少选择一种花材"
        }
    
    # 收集花材的实际颜色
    flower_colors = []
    for f in selected_flowers:
        color_field = f.get("color", "")
        for c in ['红色', '粉色', '白色', '黄色', '紫色', '蓝色', '绿色', '橙色', '香槟色']:
            if c in color_field:
                flower_colors.append(c)
    
    flower_colors = list(set(flower_colors))
    
    if color_preference and color_preference != "任意":
        color_desc = f" in {color_preference} color scheme,"
        color_keywords = f"{color_preference}"
    elif flower_colors:
        color_list = "、".join(flower_colors[:3])
        color_desc = f" featuring {color_list} tones,"
        color_keywords = color_list
    else:
        color_desc = ""
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
    
    description = call_ecnu_llm(
        system_prompt="你擅长将花材搭配转化为优美的英文描述，注意突出整体色调。",
        user_prompt=prompt,
        max_tokens=200
    )
    
    if not description:
        flower_names_str = " and ".join(flower_names[:3])
        description = (
            f"A stunning {color_keywords} bouquet of {flower_names_str}, "
            f"fresh floral arrangement with layered textures, "
            f"soft natural lighting, wrapped in kraft paper, "
            f"professional floral photography style, high quality, 8k."
        )
    
    return {
        "success": True,
        "description": description,
        "flower_names": flower_names,
        "color_theme": color_preference or "自然搭配"
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


def get_flower_type(flower_name):
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
    
    # 快速搭配
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
    
    # 基础信息
    target = st.selectbox("👤 送给谁？", ["恋人", "家人", "朋友", "老师", "自己", "客户", "孩子"])
    st.session_state.target = target
    
    occasion = st.selectbox("🎉 什么场合？", ["日常惊喜", "生日", "表白", "纪念日", "毕业", "情人节", "乔迁", "开业", "探望", "道歉", "婚礼", "年节", "母亲节"])
    st.session_state.occasion = occasion
    
    # 高级筛选折叠
    with st.expander("🎯 高级筛选（花材类型/季节/香味）", expanded=False):
        flower_type_filter = st.selectbox("🌿 花材类型", ["全部", "主花", "配花", "叶材", "果材"])
        st.session_state.flower_type_filter = flower_type_filter
        season_filter = st.selectbox("📅 适用季节", ["全年", "春季", "夏季", "秋季", "冬季"])
        st.session_state.season_filter = season_filter
        has_scent_filter = st.selectbox("🌺 香气", ["全部", "有香味", "无香味"])
        st.session_state.has_scent_filter = has_scent_filter
    
    st.markdown("---")
    
    color = st.selectbox("🎨 偏好颜色", ["任意", "粉色", "红色", "白色", "紫色", "黄色", "橙色", "蓝色", "绿色"])
    st.session_state.color = color
    
    style = st.selectbox("✨ 偏好风格", ["任意", "浪漫", "清新自然", "简约高级", "阳光活力", "复古", "可爱", "华丽大气"])
    st.session_state.style = style
    
    budget = st.selectbox("💰 预算", ["任意", "低", "中", "中高", "高"])
    st.session_state.budget = budget
    
    st.markdown("---")
    st.caption("🤖 由 ChatECNU 大模型驱动")
    st.caption("🏪 合作花店: 华东师大周边花店")
    
    # 历史记录
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 📜 历史搭配")
        for i, record in enumerate(st.session_state.history[:5]):
            if st.button(f"💐 {record['time']} · {', '.join(record['flowers'][:2])}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_flowers = record.get("selected_flowers", [])
                st.rerun()


# ========== 主区域 ==========

# ===== 灵感画廊 =====
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
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #fff, #fef5f7);
                    border-radius: 16px; padding: 15px; text-align: center;
                    border: 1px solid #eee; margin-bottom: 8px;">
            <div style="font-size: 36px;">{emoji}</div>
            <div style="font-weight: bold; font-size: 14px;">{name}</div>
            <span class="price-tag" style="font-size: 10px; display: inline-block; margin-top: 6px;">{tag}</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"✨ 试试这个", key=f"gallery_{i}", use_container_width=True):
            st.session_state.target = config["target"]
            st.session_state.occasion = config["occasion"]
            st.session_state.color = config["color"]
            st.session_state.style = config["style"]
            st.rerun()

st.markdown("---")

# ===== AI推荐按钮 =====
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("✨ AI智能推荐花材", use_container_width=True):
        with st.spinner("💐 AI花艺师正在精心搭配..."):
            # 直接调用函数而非HTTP请求
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
                st.success("✅ 推荐完成！")
                st.balloons()
            else:
                st.error("推荐失败")

st.markdown("---")

# ===== 显示推荐结果 =====
if st.session_state.recommend_result:
    result = st.session_state.recommend_result
    
    st.markdown("### 💌 AI花艺师的温馨推荐")
    st.markdown(f"""
    <div class="ai-message">
        <p>💐 {result['recommendation']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🌷 为您精选的花材")
    st.markdown("*点击花材卡片即可选择，支持多选搭配*")
    
    cols = st.columns(2)
    for idx, flower in enumerate(result["flowers"]):
        with cols[idx % 2]:
            is_selected = any(f["id"] == flower["id"] for f in st.session_state.selected_flowers)
            st.markdown(f"""
            <div class="flower-item" style="border: 2px solid {'#ff6b9d' if is_selected else '#eee'};">
                <div class="flower-visual">
                    <span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span>
                </div>
                <div class="flower-name">{flower['name']}</div>
                <div class="flower-language">「{flower['language']}」</div>
                <div style="margin: 8px 0;">
                    <span class="price-tag">💰 {flower['price_level']}</span>
                    <span style="margin-left: 8px; font-size: 11px;">🎨 {flower['color']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if is_selected:
                if st.button(f"✅ 已选", key=f"remove_{flower['id']}", use_container_width=True):
                    st.session_state.selected_flowers = [f for f in st.session_state.selected_flowers if f["id"] != flower["id"]]
                    st.rerun()
            else:
                if st.button(f"🌸 选择", key=f"select_{flower['id']}", use_container_width=True):
                    st.session_state.selected_flowers.append(flower)
                    st.rerun()
    
    # ===== 我的花篮 =====
    if st.session_state.selected_flowers:
        st.markdown("---")
        st.markdown("### 🛒 我的花篮")
        st.markdown(f"*已选择 {len(st.session_state.selected_flowers)} 种花材*")
        st.caption("💡 提示：下方序号可调整花材顺序（主花在前效果更佳）")
        
        for i, flower in enumerate(st.session_state.selected_flowers):
            col_a, col_b, col_c