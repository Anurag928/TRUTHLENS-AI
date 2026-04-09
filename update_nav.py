import os
import glob
import re

dir_path = r"c:\Users\shiva\OneDrive\Desktop\TRUTHLENS AI\Deepfake-Detection\templates"
files = glob.glob(os.path.join(dir_path, "*.html"))

nav_template = '''<header class="navbar page">
        <div class="nav-shell">
            <a class="brand" href="{{ url_for('home') }}"><span class="brand-dot"></span><span>TruthLens AI</span></a>
            <nav class="nav-links">
                <a class="{{ 'active' if request.endpoint == 'home' else '' }}" href="{{ url_for('home') }}">Home</a>
                <a class="{{ 'active' if request.endpoint == 'validate' else '' }}" href="{{ url_for('validate') }}">Detect</a>
                <a class="{{ 'active' if request.endpoint == 'dashboard' else '' }}" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="{{ 'active' if request.endpoint == 'pricing_page' else '' }}" href="{{ url_for('pricing_page') }}">Pricing</a>
                <a class="{{ 'active' if request.endpoint == 'model_page' else '' }}" href="{{ url_for('model_page') }}">Technology</a>
                {% if current_user.is_authenticated %}
                <a class="{{ 'active' if request.endpoint == 'profile' else '' }}" href="{{ url_for('profile') }}">Profile ({{ current_user.username[:10] }})</a>
                <a href="{{ url_for('logout') }}" style="color: var(--danger);">Logout</a>
                {% else %}
                <a href="{{ url_for('login') }}" style="color: var(--accent-2);">Login / Signup</a>
                {% endif %}
                <button id="theme-toggle" aria-label="Toggle Theme">🌙</button>
            </nav>
            <button class="nav-toggle" data-nav-toggle aria-expanded="false" aria-label="Toggle navigation">Menu</button>
        </div>
        <div class="mobile-menu" data-mobile-menu>
            <a class="{{ 'active' if request.endpoint == 'home' else '' }}" href="{{ url_for('home') }}">Home</a>
            <a class="{{ 'active' if request.endpoint == 'validate' else '' }}" href="{{ url_for('validate') }}">Detect</a>
            <a class="{{ 'active' if request.endpoint == 'dashboard' else '' }}" href="{{ url_for('dashboard') }}">Dashboard</a>
            <a class="{{ 'active' if request.endpoint == 'pricing_page' else '' }}" href="{{ url_for('pricing_page') }}">Pricing</a>
            <a class="{{ 'active' if request.endpoint == 'model_page' else '' }}" href="{{ url_for('model_page') }}">Technology</a>
            {% if current_user.is_authenticated %}
            <a class="{{ 'active' if request.endpoint == 'profile' else '' }}" href="{{ url_for('profile') }}">Profile ({{ current_user.username[:10] }})</a>
            <a href="{{ url_for('logout') }}" style="color: var(--danger);">Logout</a>
            {% else %}
            <a href="{{ url_for('login') }}" style="color: var(--accent-2);">Login / Signup</a>
            {% endif %}
        </div>
    </header>'''
    
theme_script = '''<script>
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
    </script>
</head>'''

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace <header>...</header>
    content = re.sub(r'<header class="navbar page">.*?</header>', nav_template, content, flags=re.DOTALL)
    
    # Inject theme script just before </head> if not already there
    if 'localStorage.getItem(\'theme\')' not in content:
        content = content.replace("</head>", theme_script)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Updated all templates")
