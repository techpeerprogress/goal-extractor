# Goal Extractor Dashboard

A comprehensive analytics system that automatically processes mastermind group conversations and extracts actionable insights including goals, marketing activities, challenges, strategies, and member engagement patterns.

## Features

- **🎯 Goal Tracking**: Automatically extracts and tracks quantifiable goals from conversations
- **📊 Marketing Analytics**: Identifies and categorizes business activities and pipeline outcomes
- **🧠 Challenge & Strategy Extraction**: Captures challenges and solutions shared in groups
- **👥 Member Engagement**: Tracks attendance, participation, and follow-up actions
- **📈 Real-time Dashboard**: Interactive Streamlit dashboard with comprehensive analytics

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone git@github.com:techpeerprogress/goal-extractor.git
   cd goal-extractor
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Run the dashboard**:
   ```bash
   streamlit run dashboard.py
   ```

5. **Process transcripts**:
   ```bash
   python main.py
   ```

## Dashboard Access

The dashboard will be available at `http://localhost:8501` with the following analytics tabs:

- **🎯 Quantifiable Goals**: Track extracted goals with specific targets
- **📊 Attendance & Achievement**: Member participation and engagement metrics
- **📈 Marketing Activities**: Business activities and pipeline outcomes
- **🧠 Challenges & Strategies**: Group challenges and solution sharing
- **📝 Member Changes**: Real-time activity and status tracking

## Technology Stack

- **Backend**: Python, Supabase
- **Frontend**: Streamlit
- **AI/ML**: Google AI API for text processing
- **Database**: PostgreSQL (via Supabase)
- **Authentication**: Supabase Auth

## Data Processing

The system automatically processes mastermind group transcripts and extracts:

- Quantifiable goals with specific targets
- Marketing activities and business outcomes
- Challenges and strategies shared
- Member attendance and engagement
- Follow-up actions and accountability tracking

## Security

- Sensitive files (credentials, API keys) are excluded from version control
- Environment variables used for configuration
- Secure database connections via Supabase

## License

This project is proprietary software. All rights reserved.

## Support

For questions or support, please contact the development team.