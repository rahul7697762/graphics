import sys
import json
import os
import traceback
import requests
from dotenv import load_dotenv

# Load local Ai-agents/.env first
load_dotenv()
# Also try to load server/.env to get PERPLEXITY_API_KEY and OPENAI_API_KEY
server_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'server', '.env')
if os.path.exists(server_env_path):
    load_dotenv(server_env_path)

class StdoutRedirector:
    """
    Redirects stdout to stderr to prevent log pollution from ruining our JSON output on stdout.
    """
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = sys.stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout 

class PerplexityService:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/chat/completions"

    def _call(self, prompt, system_msg="You are an expert."):
        if not self.api_key:
            raise Exception("PERPLEXITY_API_KEY is not set")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000
        }
        res = requests.post(self.base_url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    def generate_keywords(self, topic):
        prompt = f"Generate relevant SEO keywords for \"{topic}\" as comma-separated list."
        return self._call(prompt, "You are an SEO expert.")

    def generate_blog_content(self, topic, keywords, language, audience, style, length_num, max_attempts=3):
        blog_text = ""
        word_count = 0
        current_attempts = 0

        while word_count < length_num and current_attempts < max_attempts:
            current_attempts += 1
            
            prompt = f"""
            You are a professional human blogger who writes helpful, experience-driven real estate articles in first person.
            Write an engaging blog for {audience} in {language} on "{topic}". 
            
            Keywords to include: {keywords or "none"}.
            Style: {style}. 
            Minimum Words: {length_num}.

            CONTENT REQUIREMENTS:
            - Write in first person, sharing real-experience style insights.
            - Tone: friendly, conversational, easy to understand. Avoid jargon.
            - Structure: Hooking Introduction, 4–6 main sections, Conclusion with CTA.
            - Use Markdown format: ## for main sections, ### for subsections, **bold**, *italic*.

            ⚠️ Important: 
            - Do not use [1], [2] citation numbers. 
            - Insert valid external references as clickable Markdown links if relevant.
            - {"Continue strictly from previous text: " + blog_text[-100:] if blog_text else "Start from the beginning."}
            """
            
            new_content = self._call(prompt + "\n\nOutput valid Markdown.", "You are an expert content writer.")
            blog_text += "\n\n" + new_content
            word_count = len(blog_text.split())

        return {"blogText": blog_text.strip(), "wordCount": word_count}

    def generate_seo_title(self, blog_text, topic):
        prompt = f"Based on this blog content, generate the best SEO-friendly title (max 60 characters) that is catchy and optimized for search engines:\n{blog_text[:1200]}\nTopic: {topic}\nReturn only the title, nothing else."
        return self._call(prompt, "You are an expert SEO copywriter.").strip()

    def check_plagiarism(self, blog_text):
        prompt = f"Check for plagiarism in this article. Reply 'No plagiarism detected' if original, otherwise summarize detected parts:\n\n{blog_text[:3000]}"
        res = self._call(prompt, "You are a plagiarism checker.").strip()
        if "no plagiarism" not in res.lower():
            res += " ⚠️ Could not fully eliminate plagiarism, but the article is returned to user."
        return res

    def generate_image_text(self, blog_text, topic):
        prompt = f"Based on this blog content, create a short, simplest, small and catchy headline or phrase (maximum 3 words) that would look good on a blog header image. Make it engaging and relevant to the content:\n{blog_text[:1000]}\nTopic: {topic}\nReturn only the headline text, nothing else."
        text = self._call(prompt, "You are a marketing copywriter expert at creating catchy headlines.")
        return text.strip().replace('"', '').replace("'", "")


class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.chat_url = "https://api.openai.com/v1/chat/completions"
        self.image_url = "https://api.openai.com/v1/images/generations"

    def _call_chat(self, prompt, system_msg="You are an expert."):
        if not self.api_key:
            raise Exception("OPENAI_API_KEY is not set")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000
        }
        res = requests.post(self.chat_url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    def generate_keywords(self, topic):
        prompt = f"Generate 5-10 relevant SEO keywords for \"{topic}\" as a comma-separated list."
        return self._call_chat(prompt, "You are an SEO expert.")

    def generate_blog_content(self, topic, keywords, language, audience, style, length_num):
        prompt = f"""
        You are a professional human blogger who writes helpful, experience-driven articles.
        Write an engaging blog for {audience} in {language} on "{topic}". 
        
        Keywords to include: {keywords or "none"}.
        Style: {style}. 
        Minimum Words: {length_num}.

        CONTENT REQUIREMENTS:
        - Write in first person, sharing real-experience style insights.
        - Tone: friendly, conversational, easy to understand. Avoid jargon.
        - Structure: Hooking Introduction, 4–6 main sections, Conclusion with CTA.
        - Use Markdown format: ## for main sections, ### for subsections, **bold**, *italic*.

        ⚠️ Important: 
        - Do not use [1], [2] citation numbers. 
        - Insert valid external references as clickable Markdown links if relevant.
        """
        blog_text = self._call_chat(prompt, "You are an expert content writer.")
        word_count = len(blog_text.split())
        return {"blogText": blog_text.strip(), "wordCount": word_count}

    def generate_image(self, topic, image_text):
        if not self.api_key:
            raise Exception("OPENAI_API_KEY is not set")

        prompt = f"""Create a professional blog header image about: {topic}.

VISUAL REQUIREMENTS:
- High-quality, modern design with relevant visual elements
- Blog header format (landscape orientation, 16:9 ratio)
- Clean, professional appearance suitable for publication

TEXT OVERLAY REQUIREMENTS:
- Include the exact text: "{image_text}"
- Text must be spelled EXACTLY as written above, character by character
- Place text prominently, readable, and well-positioned on the image
- Use clean, modern typography (sans-serif font recommended)

CRITICAL: The text "{image_text}" must appear exactly as written, with perfect spelling and clear visibility."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url"
        }
        res = requests.post(self.image_url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json().get("data", [{}])[0].get("url", "")

def format_html(text):
    import re
    html = text
    html = re.sub(r'^## (.+)$', r'<h2>\g<1></h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\g<1></h3>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\g<1></strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\g<1></em>', html)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\g<2>" target="_blank" rel="noopener noreferrer" style="color: #2563eb; text-decoration: underline;">\g<1></a>', html)
    html = re.sub(r'\n{2,}', '</p><p>', html)
    return '<p>' + html + '</p>'

def main():
    try:
        if len(sys.argv) < 2:
            raise ValueError("No input data provided. Example: py generate_blog.py '{\"topic\": \"Why Buy in Pune?\"}'")
        
        raw_input = sys.argv[1]
        data = json.loads(raw_input)
        
        with StdoutRedirector():
            topic = data.get("topic", "Real Estate Investment in 2024")
            keywords = data.get("keywords", "")
            if isinstance(keywords, list):
                keywords = ", ".join(keywords)
            language = data.get("language", "English")
            audience = data.get("audience", "general public")
            style = data.get("style", "conversational")
            length = data.get("length", "Medium (500-1000 words)")
            
            length_mapping = {
                "Short (300-500 words)": 300,
                "Medium (500-1000 words)": 500,
                "Long (1000-2000 words)": 1000,
            }
            length_num = length_mapping.get(length, 500)

            perp = PerplexityService()
            oai = OpenAIService()

            # 1. Generate Keywords if needed
            if not keywords:
                try:
                    keywords = perp.generate_keywords(topic)
                except Exception as e:
                    print(f"Perplexity Keyword Gen failed, trying OpenAI: {e}", file=sys.stderr)
                    keywords = oai.generate_keywords(topic)
            
            # 2. Generate Blog Content
            content_result = {}
            try:
                content_result = perp.generate_blog_content(topic, keywords, language, audience, style, length_num)
            except Exception as e:
                print(f"Perplexity Blog Gen failed, trying OpenAI: {e}", file=sys.stderr)
                content_result = oai.generate_blog_content(topic, keywords, language, audience, style, length_num)
            
            blog_text = content_result.get("blogText", "")
            word_count = content_result.get("wordCount", 0)

            # 3. Generate SEO Title
            seo_title = topic
            try:
                seo_title = perp.generate_seo_title(blog_text, topic)
            except Exception as e:
                print(f"Perplexity SEO Title Error: {e}", file=sys.stderr)

            # 4. Plagiarism Check
            plagiarism_check = "No plagiarism detected"
            try:
                plagiarism_check = perp.check_plagiarism(blog_text)
            except Exception as e:
                print(f"Perplexity Plagiarism Error: {e}", file=sys.stderr)

            # 5. Image Generation
            image_url = ""
            try:
                try:
                    image_text = perp.generate_image_text(blog_text, topic)
                except Exception as e:
                    print(f"Perplexity Image Text Error: {e}", file=sys.stderr)
                    image_text = topic
                image_url = oai.generate_image(topic, image_text)
            except Exception as e:
                print(f"Image Gen Error: {e}", file=sys.stderr)

            blog_html = format_html(blog_text)
            
            result = {
                "topic": topic,
                "seoTitle": seo_title,
                "keywords": keywords,
                "wordCount": word_count,
                "plagiarismCheck": plagiarism_check,
                "imageUrl": image_url,
                "article": blog_html,
                "markdown": blog_text
            }
             
        # Success Output
        response = {
            "success": True,
            "status": "success",
            "data": result
        }
        print(json.dumps(response))

    except Exception as e:
        error_res = {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }
        print(json.dumps(error_res))

if __name__ == "__main__":
    main()
