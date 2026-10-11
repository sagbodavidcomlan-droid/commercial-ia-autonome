from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
import json
import os


# State
class ProductMarketingState(TypedDict):
    # Input
    product_name: str
    product_description: str
    target_audience: str
    unique_selling_points: List[str]

    # Research
    audience_insights: str
    competitor_analysis: str

    # Content per platform
    facebook_post: str
    instagram_caption: str
    tiktok_script: str
    youtube_description: str
    google_ads_copy: str

    # Image prompts
    image_prompt: str


# LLM
llm = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0.7
)


# Nodes
def research_audience(state: ProductMarketingState) -> ProductMarketingState:
    """Research target audience"""
    product = state["product_name"]
    audience = state["target_audience"]

    prompt = f"""
    I'm marketing this product: {product}
    Target audience: {audience}

    Provide:
    1. 3 key pain points of this audience
    2. 3 desires/aspirations they have
    3. What tone/language resonates with them
    4. Which platforms they're most active on

    Keep it concise and actionable.
    """

    insights = llm.invoke(prompt).content
    print(f"\n📊 Audience Insights:\n{insights}\n")
    return {"audience_insights": insights}


def analyze_competitors(state: ProductMarketingState) -> ProductMarketingState:
    """Analyze competitor marketing approaches"""
    product = state["product_name"]

    prompt = f"""
    For a product like {product}, what are common marketing approaches?

    Provide:
    1. 2-3 common marketing angles competitors use
    2. What doesn't work in competitor marketing
    3. Opportunity for differentiation

    Keep it brief and strategic.
    """

    analysis = llm.invoke(prompt).content
    print(f"\n🎯 Competitor Analysis:\n{analysis}\n")
    return {"competitor_analysis": analysis}


def create_facebook_content(state: ProductMarketingState) -> ProductMarketingState:
    """Create Facebook post - longer form, informative"""
    prompt = f"""
    Create a Facebook post for: {state['product_name']}
    Description: {state['product_description']}
    Benefits: {', '.join(state['unique_selling_points'])}
    Audience insights: {state['audience_insights']}

    Facebook post requirements:
    - Length: 150-250 words (Facebook users read longer content)
    - Start with a relatable story or question
    - Educational tone with clear benefits
    - Include 2-3 bullet points or numbered list
    - Strong CTA at the end
    - Professional but conversational tone
    - NO hashtags (not common on Facebook)
    - Can include emojis sparingly

    Format for readability with line breaks.
    """

    post = llm.invoke(prompt).content
    print(f"\n📘 Facebook Post:\n{post}\n")
    return {"facebook_post": post}


def create_instagram_content(state: ProductMarketingState) -> ProductMarketingState:
    """Create Instagram caption - visual-focused, lifestyle"""
    prompt = f"""
    Create an Instagram caption for: {state['product_name']}
    Description: {state['product_description']}
    Benefits: {', '.join(state['unique_selling_points'])}
    Audience insights: {state['audience_insights']}

    Instagram caption requirements:
    - Length: 50-100 words (people scroll fast)
    - Start with a hook that makes them stop scrolling
    - Focus on lifestyle/aspiration, not just product features
    - Use 3-5 relevant emojis naturally in the text
    - Include a question to encourage comments
    - Casual, friendly, authentic tone
    - End with 8-12 hashtags (mix of popular and niche)
    - Hashtags should be on separate lines after the caption

    Remember: Instagram is visual-first, caption supports the image.
    """

    caption = llm.invoke(prompt).content
    print(f"\n📸 Instagram Caption:\n{caption}\n")
    return {"instagram_caption": caption}


def create_tiktok_content(state: ProductMarketingState) -> ProductMarketingState:
    """Create TikTok script - short, entertaining, trend-focused"""
    prompt = f"""
    Create a TikTok video script (15-30 seconds) for: {state['product_name']}
    Description: {state['product_description']}
    Benefits: {', '.join(state['unique_selling_points'])}
    Audience insights: {state['audience_insights']}

    TikTok script requirements:
    - Hook in first 1-3 seconds (controversial/surprising/relatable)
    - Fast-paced, dynamic content
    - Show product in action with visual demonstrations
    - Use trending audio/sound suggestions
    - Text overlay suggestions for key points
    - Casual, authentic, entertaining tone
    - Include engagement trigger (duet/stitch suggestion)
    - End with strong CTA

    Format:
    [0-3 sec]: Hook + text overlay
    [3-15 sec]: Main content with 3 quick points
    [15-20 sec]: Product demo
    [20-25 sec]: CTA
    [Audio suggestion]: ...
    [Hashtags]: 4-5 trending + niche hashtags

    Remember: TikTok is entertainment-first, education second.
    """

    script = llm.invoke(prompt).content
    print(f"\n🎵 TikTok Script:\n{script}\n")
    return {"tiktok_script": script}


def create_youtube_content(state: ProductMarketingState) -> ProductMarketingState:
    """Create YouTube description - SEO-optimized, detailed"""
    prompt = f"""
    Create a YouTube video description for: {state['product_name']}
    Description: {state['product_description']}
    Benefits: {', '.join(state['unique_selling_points'])}
    Audience insights: {state['audience_insights']}

    YouTube description requirements:
    - Opening paragraph (2-3 sentences) - most visible, include key info
    - Timestamps with topics (00:00 Intro, 01:30 Feature 1, etc.)
    - Detailed product information (people search here for details)
    - Links section:
      * Product link
      * Social media links
      * Related videos
    - About section (who you are, what you do)
    - SEO keywords naturally woven in
    - 10-15 relevant hashtags at the end
    - Professional, informative tone

    Remember: YouTube is search-based, optimize for discovery.
    """

    description = llm.invoke(prompt).content
    print(f"\n🎬 YouTube Description:\n{description}\n")
    return {"youtube_description": description}


def create_google_ads_content(state: ProductMarketingState) -> ProductMarketingState:
    """Create Google Ads copy - conversion-focused, clear value"""
    prompt = f"""
    Create 3 variations of Google Search Ads for: {state['product_name']}
    Description: {state['product_description']}
    Benefits: {', '.join(state['unique_selling_points'])}
    Audience insights: {state['audience_insights']}

    Google Ads requirements (STRICT character limits):
    - Headline 1: Max 30 characters - main benefit/hook
    - Headline 2: Max 30 characters - secondary benefit/USP
    - Headline 3: Max 30 characters - CTA or offer
    - Description 1: Max 90 characters - expand on benefits
    - Description 2: Max 90 characters - overcome objections/add urgency

    Ad copy best practices:
    - Include numbers/specific claims when possible
    - Use power words (Free, New, Limited, Exclusive)
    - Address pain point immediately
    - Clear value proposition
    - Strong CTA
    - Match search intent

    Create 3 variations:
    Variation 1: Benefit-focused
    Variation 2: Problem-solution focused
    Variation 3: Offer/urgency focused

    Format each variation clearly with character counts.
    """

    ads = llm.invoke(prompt).content
    print(f"\n🔍 Google Ads:\n{ads}\n")
    return {"google_ads_copy": ads}


def create_image_prompt(state: ProductMarketingState) -> ProductMarketingState:
    """Create detailed image generation prompt"""
    prompt = f"""
    Create a detailed image generation prompt for: {state['product_name']}
    Description: {state['product_description']}
    Target audience: {state['target_audience']}

    The prompt should describe:
    - The product in use/action (lifestyle shot, not just product)
    - Setting/environment that resonates with target audience
    - Lighting and mood (professional, warm, energetic, etc.)
    - Color palette (specific colors that match brand/mood)
    - Composition (close-up, wide shot, angle)
    - Style (photorealistic, minimalist, vibrant, etc.)
    - Any people (if relevant - describe demographics, expression, activity)
    - Emotion/feeling the image should evoke

    Output: One detailed prompt in English, 80-120 words, optimized for AI image generation (DALL-E, Midjourney, Stable Diffusion).
    """

    image_prompt = llm.invoke(prompt).content
    print(f"\n🎨 Image Generation Prompt:\n{image_prompt}\n")
    return {"image_prompt": image_prompt}


def save_to_files(state: ProductMarketingState) -> ProductMarketingState:
    """Save all content to files"""
    product_name = state['product_name'].replace(" ", "_")
    output_dir = f"output_{product_name}"

    # Create directory
    os.makedirs(output_dir, exist_ok=True)

    # Prepare content
    content = {
        "product_info": {
            "name": state["product_name"],
            "description": state["product_description"],
            "target_audience": state["target_audience"],
            "usps": state["unique_selling_points"]
        },
        "research": {
            "audience_insights": state.get("audience_insights", ""),
            "competitor_analysis": state.get("competitor_analysis", "")
        },
        "content": {
            "facebook": state.get("facebook_post", ""),
            "instagram": state.get("instagram_caption", ""),
            "tiktok": state.get("tiktok_script", ""),
            "youtube": state.get("youtube_description", ""),
            "google_ads": state.get("google_ads_copy", "")
        },
        "creative": {
            "image_prompt": state.get("image_prompt", "")
        }
    }

    # Save JSON
    with open(f"{output_dir}/marketing_content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    # Save separate TXT for each platform
    for platform, text in content["content"].items():
        with open(f"{output_dir}/{platform}.txt", "w", encoding="utf-8") as f:
            f.write(text)

    # Save image prompt separately
    with open(f"{output_dir}/image_prompt.txt", "w", encoding="utf-8") as f:
        f.write(content["creative"]["image_prompt"])

    print(f"\n💾 All content saved to: {output_dir}/")
    print(f"   - marketing_content.json (all content)")
    print(f"   - facebook.txt")
    print(f"   - instagram.txt")
    print(f"   - tiktok.txt")
    print(f"   - youtube.txt")
    print(f"   - google_ads.txt")
    print(f"   - image_prompt.txt")

    return {}


# Build graph
workflow = StateGraph(ProductMarketingState)

# Add nodes
workflow.add_node("research_audience", research_audience)
workflow.add_node("analyze_competitors", analyze_competitors)
workflow.add_node("facebook", create_facebook_content)
workflow.add_node("instagram", create_instagram_content)
workflow.add_node("tiktok", create_tiktok_content)
workflow.add_node("youtube", create_youtube_content)
workflow.add_node("google_ads", create_google_ads_content)
workflow.add_node("image_prompt", create_image_prompt)
workflow.add_node("save", save_to_files)

# Define flow
workflow.set_entry_point("research_audience")
workflow.add_edge("research_audience", "analyze_competitors")
workflow.add_edge("analyze_competitors", "facebook")
workflow.add_edge("facebook", "instagram")
workflow.add_edge("instagram", "tiktok")
workflow.add_edge("tiktok", "youtube")
workflow.add_edge("youtube", "google_ads")
workflow.add_edge("google_ads", "image_prompt")
workflow.add_edge("image_prompt", "save")
workflow.add_edge("save", END)

# Compile
app = workflow.compile()

# Run
if __name__ == "__main__":
    print("🚀 Product Marketing Agent Starting...\n")
    print("=" * 60)

    # INSERT YOUR PRODUCT DETAILS HERE
    initial_state = {
        "product_name": "Smart Water Bottle",
        "product_description": "A smart water bottle with hydration tracking, LED reminders, and app connectivity to help you stay hydrated throughout the day",
        "target_audience": "Health-conscious professionals aged 25-40 who work in offices and struggle to drink enough water",
        "unique_selling_points": [
            "Smart LED reminders based on your activity level",
            "Automatic syncing to mobile app",
            "Sleek, minimalist design",
            "Week-long battery life",
            "BPA-free and eco-friendly"
        ]
    }

    result = app.invoke(initial_state)

    print("=" * 60)
    print("✅ Marketing content generation complete!")
    print("📁 Check the output folder for all platform-specific content")