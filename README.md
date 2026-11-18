# Lead & Invoice Extractor

Reads incoming business emails and logs each one as a spreadsheet row: who wrote, how to reach
them, what they want, how much money is involved and how urgent it is.

## The problem it solves

In a small business, enquiries, orders and invoice questions arrive as free-form emails. Someone
has to open each one, work out the details and type them into a spreadsheet or CRM. That takes a few
minutes per email, it gets skipped on busy days, and the urgent message sits unread under ten
routine ones.

This dashboard does that reading and typing. Every message becomes one structured row, urgent ones
are flagged, and the result is written to `extracted_leads.xlsx`, ready to sort, filter or import.

For each message it extracts:

| Field | Example |
|---|---|
| Client Name | Elena Marsh |
| Email | accounts@hartwellbakery.example |
| Phone | +1 (646) 555-0171 |
| Type | Inquiry, Order or Invoice |
| Service Requested | Social media management |
| Amount and Currency | 2,350.00 USD |
| Urgency | High, Medium or Low |

The summary bar shows the number of messages processed, how many are high urgency, and the total
value of the amounts found.

## Quick start (Windows)

Requires [Python 3.10 or newer](https://www.python.org/downloads/).

**Easiest:** double-click `run.bat`. The first run installs everything, then the dashboard opens in your browser.

**Or run the commands yourself** from this folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

On macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

The dashboard opens at http://localhost:8501. Press `Ctrl+C` in the terminal to stop it.

## Try it

1. The sample inbox holds five emails written the way real ones arrive: typos, a forwarded thread,
   signatures, phone numbers in four formats. Open **Read the emails as they arrived** to see them.
2. Click **Run AI Automation**. The table fills in and the summary bar updates.
3. Paste any email or message of your own into the box on the right and run again.
4. Click **Download Excel** or **Download CSV**. The Excel file is also saved to `output/extracted_leads.xlsx`.

No email account is connected. The sample inbox stands in for one so the workflow can be shown
without mail server credentials.

## Demo Mode and AI Mode

| | Demo Mode | AI Mode |
|---|---|---|
| Needs an API key | No | Yes |
| How it reads a message | Fixed patterns (regular expressions and keyword lists) | An AI model reads the whole message |
| Handles unusual wording | Often not | Yes |
| Use it for | Trying the dashboard, demos | Real email |

Demo Mode is on by default when no key is configured. To switch to AI Mode:

1. Copy `.env.example` to `.env`.
2. Paste **one** key:
   - Anthropic: `ANTHROPIC_API_KEY=...` (https://console.anthropic.com)
   - OpenAI: `OPENAI_API_KEY=...` (https://platform.openai.com)
   - Google Gemini: `GEMINI_API_KEY=...` (https://aistudio.google.com/apikey)
3. Restart the dashboard. The sidebar shows the provider and model in use.

Never share your `.env` file or commit it to Git; `.gitignore` already excludes it.

| Setting | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | Which provider to use when more than one key is set: `anthropic`, `openai` or `gemini` |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | `claude-sonnet-5-5` and `claude-haiku-5-5` cost less |
| `OPENAI_MODEL` | `gpt-4o-mini` | Set to a chat model available on your account |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Any Gemini model your key can use |

Gemini offers a free tier. On it, Google may use the text you send to improve its products, so use the free tier for testing with sample data and a paid key for real client data.

## Project layout

| File | Role |
|---|---|
| `app.py` | The dashboard: summary bar, inbox, results table, downloads |
| `automation/models.py` | The `Lead` schema: the fields and the rules for filling them |
| `automation/extractor_ai.py` | AI extraction with Claude, OpenAI or Gemini, validated against the schema |
| `automation/extractor_rules.py` | Demo Mode extraction by pattern matching |
| `automation/export.py` | Summary numbers and the formatted Excel file |
| `automation/sample_emails.py` | The five sample emails |
| `automation/config.py` | Settings from `.env` |
| `tests/smoke_test.py` | End-to-end check, no API key needed |

Run the check with:

```powershell
.venv\Scripts\python.exe tests\smoke_test.py
```

## Notes for developers

- **Connecting a real inbox.** The extractors take a `Message(source, raw)`. To process live mail,
  fetch messages over IMAP, the Gmail API or Microsoft Graph, build `Message` objects and pass them to
  `extract_with_ai`. Nothing else changes.
- **Adding a field.** Add it to `Lead` in `automation/models.py` with a description. The AI extractor
  picks it up from the schema; add it to `COLUMNS` to show and export it.
- **Structured output.** With Claude, the response is constrained to the `Lead` schema, so a row is
  either valid or the message is reported as failed. Urgency and type cannot take unexpected values.
- **Amounts.** For a range the lower figure is recorded. The summary total covers the most common
  currency only and says so when others are present.
- **Refusal fallback.** For current Claude models the request opts in to the server-side fallback
  (`fallbacks="default"`), so a message declined by a safety classifier is retried on another model
  instead of failing. Remove `betas` and `fallbacks` in `automation/extractor_ai.py` to turn it off.
- **Privacy.** In AI Mode the text of each message is sent to the chosen AI provider. Demo Mode sends
  nothing anywhere.
