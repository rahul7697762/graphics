import random

from app.templates import (
    template1,
    template2,
    template3,
    template4,
)

# Template registry with metadata
TEMPLATES = {
    "classic": {
        "render": template1.render,
        "name": "Classic Elegant",
        "description": "Timeless design with gradient overlay and ribbon CTA",
        "preview_color": "#E63946"
    },
    "modern": {
        "render": template2.render,
        "name": "Modern Bold",
        "description": "Contemporary layout with bold typography",
        "preview_color": "#3B82F6"
    },
    "minimal": {
        "render": template3.render,
        "name": "Minimal Clean",
        "description": "Clean minimalist design with focus on visuals",
        "preview_color": "#10B981"
    },
    "luxury": {
        "render": template4.render,
        "name": "Premium Luxury",
        "description": "High-end luxury aesthetic with golden accents",
        "preview_color": "#F59E0B"
    }
}

# Aliases for easier access (template1, template2, etc.)
TEMPLATE_ALIASES = {
    "template1": "classic",
    "template2": "modern",
    "template3": "minimal",
    "template4": "luxury"
}

# List for random selection
TEMPLATE_LIST = list(TEMPLATES.values())


def pick_template(template_id: str = None):
    """
    Select a poster template.
    
    Args:
        template_id: Optional specific template ID to use.
                     Accepts: classic, modern, minimal, luxury, template1, template2, template3, template4
                     If None or 'random', a random template is selected.
    
    Returns:
        The render function for the selected template
    """
    if template_id and template_id != 'random':
        # Resolve alias if provided (template1 -> classic, etc.)
        resolved_id = TEMPLATE_ALIASES.get(template_id, template_id)
        if resolved_id in TEMPLATES:
            return TEMPLATES[resolved_id]["render"]
    
    # Random selection
    return random.choice(TEMPLATE_LIST)["render"]


def get_template_info(template_id: str):
    """Get metadata for a specific template"""
    if template_id in TEMPLATES:
        return {
            "id": template_id,
            **TEMPLATES[template_id]
        }
    return None


def list_templates():
    """Return list of all available templates with metadata"""
    return [
        {
            "id": tid,
            "name": tmpl["name"],
            "description": tmpl["description"],
            "preview_color": tmpl["preview_color"]
        }
        for tid, tmpl in TEMPLATES.items()
    ]
