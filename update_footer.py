import os
import glob
import re

dir_path = r"c:\Users\shiva\OneDrive\Desktop\TRUTHLENS AI\Deepfake-Detection\templates"
files = glob.glob(os.path.join(dir_path, "*.html"))

footer_template = '''<footer class="footer">
            <p class="small">TruthLens AI &copy; 2026</p>
            <div class="row">
                <a href="{{ url_for('home') }}">Home</a>
                <a href="{{ url_for('validate') }}">Detect</a>
                <a href="{{ url_for('dashboard') }}">Dashboard</a>
                <a href="{{ url_for('pricing_page') }}">Pricing</a>
                <a href="{{ url_for('model_page') }}">Technology</a>
                <a href="{{ url_for('profile') }}">Profile</a>
            </div>
        </footer>'''

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace <footer class="footer">...</footer>
    content = re.sub(r'<footer class="footer">.*?</footer>', footer_template, content, flags=re.DOTALL)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Updated all footers")
