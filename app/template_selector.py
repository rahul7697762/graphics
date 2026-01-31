import random

from app.templates import (
    template_1,
    template_2,
    template_3,
    template_4,
)

# List of available template render functions
TEMPLATES = [
    template_1.render,
    template_2.render,
    template_3.render,
    template_4.render,
]


def pick_template():
    """
    Randomly select a poster template
    """
    return random.choice(TEMPLATES)
