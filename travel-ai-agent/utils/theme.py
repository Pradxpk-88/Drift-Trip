def get_theme_css(dark_mode: bool) -> str:
    if not dark_mode:
        return """
        :root {
            --bg-main: #f0f1ea;
            --bg-card: #ffffff;
            --text-main: #1d2415;
            --text-muted: #697857;
            --border: #d8dcc7;
            --accent: #516140;
        }

        .stApp {
            background: var(--bg-main);
            color: var(--text-main);
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }

        .title {
            text-align: center;
            font-size: 4rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .tagline {
            text-align: center;
            color: var(--text-muted);
        }
        """

    return """
    :root {
        --bg-main: #1d2415;
        --bg-card: #37432b;
        --text-main: #f8f8f2;
        --text-muted: #8b907c;
        --border: #516140;
        --accent: #697857;
    }

    .stApp {
        background: var(--bg-main);
        color: var(--text-main);
    }

    .card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px;
    }

    .title {
        text-align: center;
        font-size: 4rem;
        font-weight: 700;
        color: var(--text-main);
    }

    .tagline {
        text-align: center;
        color: var(--text-muted);
    }
    """