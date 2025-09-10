# Claude API Setup Guide

This guide will help you set up the Claude API key for AI-powered job title extraction.

## 🔑 Step 1: Get Claude API Key

1. **Visit Anthropic Console**: https://console.anthropic.com/
2. **Sign up/Login** to your Anthropic account
3. **Navigate to API Keys** section
4. **Create new API key** (click "Create Key" or "Generate API Key")
5. **Copy the API key** (starts with `sk-ant-api03-...`)

⚠️ **Important**: Keep this key secure and never share it publicly!

## 🔧 Step 2: Set Up Environment

### Option A: Create .env file (Recommended)

```bash
# Create .env file with your API key
echo 'ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here' > .env
```

### Option B: Export environment variable

```bash
# For current session
export ANTHROPIC_API_KEY='sk-ant-api03-your-actual-key-here'

# For permanent setup (add to ~/.bashrc or ~/.zshrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-actual-key-here"' >> ~/.bashrc
```

## ✅ Step 3: Verify Setup

Run the API key checker:

```bash
python utilities/check_api_key.py
```

Expected output:
```
🔍 Claude API Key Check
==============================
✅ API key found: sk-ant-api03-...
✅ Format looks correct
🧪 Testing API connection...
✅ API test successful!
🎉 Claude API is properly configured!
```

## 🚀 Step 4: Run AI Job Title Extraction

### Safe Test (Recommended First)
```bash
# Test with 2 organizations, no database changes
python utilities/ai_job_titles_updater.py --test --limit 2
```

### Small Production Run
```bash
# Process 5 organizations with database updates
python utilities/ai_job_titles_updater.py --limit 5
```

### Full Production Run
```bash
# Process all organizations (requires confirmation)
python utilities/ai_job_titles_updater.py
```

## 💰 Cost Estimates

- **Test (2 orgs)**: ~$0.10
- **Small (5 orgs)**: ~$0.25
- **Medium (20 orgs)**: ~$1.00  
- **Full (390 orgs)**: ~$20-50

## 🛠️ Troubleshooting

### Issue: "No ANTHROPIC_API_KEY found"
**Solution**: 
```bash
# Check if .env file exists and has the key
cat .env

# If using .env, load it:
source .env  # or set -a; source .env; set +a

# Verify it's loaded:
echo $ANTHROPIC_API_KEY
```

### Issue: "API key format looks incorrect"
**Solution**: Ensure your key starts with `sk-ant-api03-`

### Issue: "anthropic package not installed"
**Solution**:
```bash
pip install anthropic
```

### Issue: "API test failed"
**Solutions**:
- Check your API key is correct
- Verify your Anthropic account has credits
- Check internet connection
- Try generating a new API key

## 🔒 Security Best Practices

1. **Never commit .env files** (already in .gitignore)
2. **Don't share API keys** in code, emails, or chat
3. **Rotate keys periodically** 
4. **Monitor usage** in Anthropic Console
5. **Set spending limits** if available

## 📋 Available Scripts

| Script | Purpose |
|--------|---------|
| `setup_claude_api.py` | Setup guide and environment check |
| `utilities/check_api_key.py` | Verify API key configuration |
| `utilities/ai_job_titles_updater.py` | Main AI extraction script |
| `utilities/test_ai_job_titles.py` | Test AI functionality |
| `run_ai_job_titles_update.py` | Production runner guide |

## 🎯 Expected Results

After successful extraction, your MongoDB will have:

```json
{
  "name": "Organization Name",
  "job_titles": [
    "Software Engineer",
    "Program Manager", 
    "Data Scientist",
    "Marketing Coordinator"
  ],
  "job_titles_extraction_method": "claude_ai",
  "job_titles_updated_at": "2025-09-09T19:30:00.000Z"
}
```

## 🆘 Need Help?

1. **Run setup helper**: `python setup_claude_api.py`
2. **Check API setup**: `python utilities/check_api_key.py`
3. **Test extraction**: `python utilities/test_ai_job_titles.py`

Happy extracting! 🤖✨