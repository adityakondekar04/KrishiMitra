from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "List available Gemini models and their supported generation methods (requires GEMINI_API_KEY)."

    def handle(self, *args, **options):
        try:
            import google.generativeai as genai
        except Exception:
            self.stderr.write(self.style.ERROR("google-generativeai not installed. pip install google-generativeai"))
            return
        if not getattr(settings, 'GEMINI_API_KEY', ''):
            self.stderr.write(self.style.ERROR("GEMINI_API_KEY not set. Set env var or in settings.py."))
            return
        genai.configure(api_key=settings.GEMINI_API_KEY)
        try:
            models = list(genai.list_models())
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to list models: {e}"))
            return
        if not models:
            self.stdout.write("No models returned.")
            return
        for m in models:
            name = getattr(m, 'name', '')
            methods = getattr(m, 'supported_generation_methods', []) or []
            self.stdout.write(f"- {name} | methods: {', '.join(methods)}")
        self.stdout.write("\nTip: Set GEMINI_MODEL to one of the names above that supports 'generateContent'.")