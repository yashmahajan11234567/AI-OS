# FreeLLMAPI Initial Configuration Guide

## Current Status
✅ FreeLLMAPI server is running at http://127.0.0.1:3001
✅ API endpoints are accessible (/ and /api/ping return 200)
❌ No providers configured yet (API requires authentication)

## Configuration Steps

### 1. Access the Dashboard
Open your web browser and go to: **http://127.0.0.1:3001**

### 2. First-Time Setup
- On first visit, you'll see a login/register page
- Create a new account (email + password) - this is local-only for desktop/server installs
- After login, you'll be directed to the dashboard

### 3. Add Provider Keys
Navigate to the **Keys** page in the dashboard:
- Click "Add Key" or "+" button
- Select a provider from the list
- Enter your API key for that provider (obtain from provider's website)
- Give the key a label (e.g., "main", "free-tier")
- Save the key

### 4. Recommended Free Providers
Choose providers with genuinely free tiers (no paid subscription required):

| Provider | Free Tier Details | Best For |
|----------|-------------------|----------|
| **Groq** | Very fast, generous daily limits | General reasoning, coding |
| **Google Gemini** | Good free tier with generous limits | General use, multimodal |
| **Hugging Face** | Free inference API | Various models |
| **Mistral** | Free tier available | Reasoning, coding |
| **OpenRouter** | Aggregates multiple free providers | Variety of models |
| **Cerebras** | Very fast for certain models | Specific workloads |

### 5. Post-Configuration Verification
After adding at least one provider:

#### Verify Provider Registration
- Keys page should show your provider with a status indicator (green/healthy)
- No error messages should appear

#### Check Model Availability
- Visit the **Models** page
- You should see a list of available models from your configured provider(s)
- Models should show status scores (reliability, speed, intelligence)

#### Identify Suitable Models
Look for these model categories:

**General Reasoning:**
- Look for models labeled as "reasoning", "chat", or general-purpose LLMs
- Examples: llama-3.x, mistral, gemini-pro, claude-like models (if available)

**Coding:**
- Models specifically trained for code: codellama, deepseek-coder, starcoder
- Or general models with strong coding abilities

**Long-Context Work:**
- Models with context windows > 8K tokens
- Look for 16K, 32K, 128K context variants
- Examples: certain llama-3 variants, claude-like models with extended context

#### Configure Fallback Chain (Optional but Recommended)
If you configure 2+ providers:
- Go to Keys page → "Fallback Chain" section
- Drag providers to set priority order
- Higher priority = tried first
- Enable automatic fallback on rate limits/errors

#### Verify Unified API Key
- Once provider is configured, your **unified API key** will appear in the dashboard header
- Format: `freellmapi-[identifier]`
- **DO NOT share or expose this key**
- This is what AI-OS will use to connect to FreeLLMAPI

#### Confirm Endpoint Status
- OpenAI-compatible endpoint remains: **http://127.0.0.1:3001/v1**
- Anthropic Messages API also available at same base URL

## Important Security Notes
- 🔐 **Never share API keys** - enter them only in the FreeLLMAPI dashboard
- 🔐 **Never expose the unified API key** in chats, terminals, or logs
- 🔐 Provider keys are stored encrypted locally
- 🔐 Only the unified key leaves FreeLLMAPI (to your applications)

## Next Steps
Once you have at least one provider configured and verified:
1. Return to this conversation
2. I'll help you verify the configuration and create the final report
3. Do NOT attempt to connect AI-OS yet - that happens in a later controlled step

## Troubleshooting
- If you see errors, check the provider's website for service status
- Some providers may require enabling billing (but still offer free tiers)
- FreeLLMAPI automatically tests keys and shows health status
- Consult the FreeLLMAPI documentation if needed