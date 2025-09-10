# 🚀 Quick Start: AI Job Title Extraction

## Step 1: Get Your Claude API Key
1. Visit: https://console.anthropic.com/
2. Sign up/login
3. Go to "API Keys" 
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-api03-...`)

## Step 2: Set Up API Key
Choose one option:

### Option A: Environment Variable (Quick)
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-your-actual-key-here'
```

### Option B: .env File (Persistent)
```bash
echo 'ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here' > .env
```

## Step 3: Verify Setup
```bash
python3 verify_ai_setup.py
```

Should show:
```
🎉 Setup is ready!
✅ You can run AI job title extraction
```

## Step 4: Run AI Extraction

### Safe Test (Recommended First)
```bash
python utilities/ai_job_titles_updater.py --test --limit 2
```
- Cost: ~$0.10
- Time: 2-3 minutes  
- No database changes

### Small Production Run
```bash
python utilities/ai_job_titles_updater.py --limit 5
```
- Cost: ~$0.25
- Time: 5-10 minutes
- Updates 5 organizations

### Full Production
```bash
python utilities/ai_job_titles_updater.py
```
- Cost: ~$20-50
- Time: 2-3 hours
- Updates all 390+ organizations
- Requires confirmation

## Troubleshooting

### Missing packages?
```bash
source venv/bin/activate
pip install anthropic pymongo
```

### API key not working?
```bash
python utilities/check_api_key.py
```

### Need help?
```bash
python3 setup_claude_api.py
```

## 🎯 What You'll Get

After running, each organization in MongoDB will have:
```json
{
  "job_titles": ["Software Engineer", "Data Scientist", "Program Manager"],
  "job_titles_extraction_method": "claude_ai", 
  "job_titles_updated_at": "2025-09-09T20:00:00Z"
}
```

Ready to extract precise job titles with AI! 🤖✨