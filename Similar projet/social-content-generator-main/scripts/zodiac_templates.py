#!/usr/bin/env python3
"""
12 Zodiac Templates + Advanced Features
Complete template configurations for all zodiac signs
"""

# All 12 zodiac sign configurations
ZODIAC_TEMPLATES = {
    # Fire Signs
    "aries": {
        "name": "Aries ♈",
        "element": "fire",
        "keywords": ["bold", "energetic", "passionate", "courageous", "leader", "competitive", "dynamic"],
        "color_primary": "#FF4B4B",  # Vibrant Red
        "color_secondary": "#FFD700",  # Gold
        "color_bg": "#2D1B1B",
        "mood": "upbeat",
        "font": "Arial-Bold",
        "animation": "zoom_fan",
        "text_effect": "rainbow",
        "transition": "center"
    },
    "leo": {
        "name": "Leo ♌",
        "element": "fire",
        "keywords": ["confident", "charismatic", "dramatic", "creative", "generous", "royal", "warm"],
        "color_primary": "#FF8C00",  # Orange
        "color_secondary": "#FFD700",  # Gold
        "color_bg": "#2D1B0A",
        "mood": "epic",
        "font": "Georgia-Bold",
        "animation": "zoom_fan",
        "text_effect": "rainbow",
        "transition": "center"
    },
    "sagittarius": {
        "name": "Sagittarius ♐",
        "element": "fire",
        "keywords": ["adventurous", "optimistic", "philosophical", "free-spirited", "curious", "honest"],
        "color_primary": "#8B4513",  # Saddle Brown
        "color_secondary": "#FFD700",
        "color_bg": "#2D1B0A",
        "mood": "upbeat",
        "font": "Arial-Bold",
        "animation": "zoom_fan",
        "text_effect": "rainbow",
        "transition": "center"
    },
    
    # Earth Signs
    "taurus": {
        "name": "Taurus ♉",
        "element": "earth",
        "keywords": ["patient", "reliable", "devoted", "responsible", "stable", "sensual", "practical"],
        "color_primary": "#228B22",  # Forest Green
        "color_secondary": "#DAA520",  # Goldenrod
        "color_bg": "#1B2D1B",
        "mood": "ambient",
        "font": "Times-Bold",
        "animation": "fade",
        "text_effect": "shadow",
        "transition": "left"
    },
    "virgo": {
        "name": "Virgo ♍",
        "element": "earth",
        "keywords": ["analytical", "modest", "hardworking", "meticulous", "helpful", "pure", "organized"],
        "color_primary": "#6B8E23",  # Olive Drab
        "color_secondary": "#CD853F",  # Peru
        "color_bg": "#1B2D1B",
        "mood": "lofi",
        "font": "Courier-Bold",
        "animation": "fade",
        "text_effect": "shadow",
        "transition": "right"
    },
    "capricorn": {
        "name": "Capricorn ♑",
        "element": "earth",
        "keywords": ["ambitious", "disciplined", "patient", "practical", "responsible", "traditional", "determined"],
        "color_primary": "#2F4F4F",  # Dark Slate Gray
        "color_secondary": "#DAA520",
        "color_bg": "#1B2D2D",
        "mood": "cinematic",
        "font": "Times-Bold",
        "animation": "fade",
        "text_effect": "shadow",
        "transition": "bottom"
    },
    
    # Air Signs
    "gemini": {
        "name": "Gemini ♊",
        "element": "air",
        "keywords": ["versatile", "curious", "communicative", "playful", "adaptable", "quick", "witty"],
        "color_primary": "#FFD700",  # Gold
        "color_secondary": "#4B0082",  # Indigo
        "color_bg": "#2D1B4B",
        "mood": "happy",
        "font": "Arial-Bold",
        "animation": "blur",
        "text_effect": "blink",
        "transition": "center"
    },
    "libra": {
        "name": "Libra ♎",
        "element": "air",
        "keywords": ["diplomatic", "graceful", "peaceful", "idealistic", "social", "balanced", "charming"],
        "color_primary": "#FFB6C1",  # Light Pink
        "color_secondary": "#C0C0C0",  # Silver
        "color_bg": "#2D1B3D",
        "mood": "ambient",
        "font": "Georgia-Bold",
        "animation": "blur",
        "text_effect": "box",
        "transition": "left"
    },
    "aquarius": {
        "name": "Aquarius ♒",
        "element": "air",
        "keywords": ["innovative", "humanitarian", "independent", "intellectual", "visionary", "unique", "progressive"],
        "color_primary": "#00BFFF",  # Deep Sky Blue
        "color_secondary": "#E0FFFF",  # Light Cyan
        "color_bg": "#1B2D4B",
        "mood": "beats",
        "font": "Helvetica-Bold",
        "animation": "blur",
        "text_effect": "blink",
        "transition": "right"
    },
    
    # Water Signs
    "cancer": {
        "name": "Cancer ♋",
        "element": "water",
        "keywords": ["emotional", "intuitive", "nurturing", "protective", "sympathetic", "loyal", "caring"],
        "color_primary": "#ADD8E6",  # Light Blue
        "color_secondary": "#C0C0C0",
        "color_bg": "#1B2D3D",
        "mood": "lofi",
        "font": "Times-Bold",
        "animation": "zoom_fan",
        "text_effect": "rainbow",
        "transition": "bottom"
    },
    "scorpio": {
        "name": "Scorpio ♏",
        "element": "water",
        "keywords": ["passionate", "resourceful", "brave", "determined", "mysterious", "intense", "transforming"],
        "color_primary": "#8B0000",  # Dark Red
        "color_secondary": "#FF4500",  # Orange Red
        "color_bg": "#2D1B1B",
        "mood": "dark",
        "font": "Arial-Bold",
        "animation": "zoom_fan",
        "text_effect": "shadow",
        "transition": "center"
    },
    "pisces": {
        "name": "Pisces ♓",
        "element": "water",
        "keywords": ["compassionate", "artistic", "intuitive", "gentle", "wise", "dreamy", "selfless"],
        "color_primary": "#9370DB",  # Medium Purple
        "color_secondary": "#FFB6C1",
        "color_bg": "#2D1B4B",
        "mood": "ambient",
        "font": "Georgia-Bold",
        "animation": "fade",
        "text_effect": "rainbow",
        "transition": "left"
    }
}

# Additional video effect configurations
VIDEO_EFFECTS = {
    "fade": {
        "in_filter": "fade=t=in:st=0:d=1",
        "out_filter": "fade=t=out:st={duration-1}:d=1",
        "transition_filter": "fade"
    },
    "zoom_fan": {
        "in_filter": "zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125",
        "out_filter": "",
        "transition_filter": "zoom"
    },
    "blur": {
        "in_filter": "boxblur=10:enable='between(t,0,1)'",
        "out_filter": "boxblur=10:enable='between(t,{duration-1},{duration})'",
        "transition_filter": "boxblur=5"
    },
    "rainbow": {
        "in_filter": "hue=H=360*t/10:s=1",
        "out_filter": "",
        "transition_filter": "hue"
    }
}

# Text animation configurations
TEXT_ANIMATIONS = {
    "fade_in_out": {
        "alpha": "if(lt(t,1), t/1, if(gt(t,{duration}-1), (t-({duration}-1))/1, 1))"
    },
    "slide_left": {
        "x": "if(lt(t,1), w - (w * t/1), w)"
    },
    "slide_right": {
        "x": "if(lt(t,1), w - (w * t/1), w)"
    },
    "slide_up": {
        "y": "if(lt(t,1), h - (h * t/1), h)"
    },
    "slide_down": {
        "y": "if(lt(t,1), h - (h * t/1), h)"
    },
    "zoom": {
        "fontsize": "if(lt(t,1), 20 + (size * t/1), size)"
    },
    "blink": {
        "alpha": "if(mod(t,1), 1, 0.3)"
    }
}

def get_zodiac_template(zodiac_name: str) -> dict:
    """Get template config for a zodiac sign"""
    zodiac_name = zodiac_name.lower()
    return ZODIAC_TEMPLATES.get(zodiac_name, ZODIAC_TEMPLATES["aries"])

def get_all_zodiac_names() -> list:
    """Get list of all zodiac sign names"""
    return list(ZODIAC_TEMPLATES.keys())

def get_zodiac_by_element(element: str) -> list:
    """Get zodiac signs by element (fire, earth, air, water)"""
    return [name for name, config in ZODIAC_TEMPLATES.items() if config["element"] == element]