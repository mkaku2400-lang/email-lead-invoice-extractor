"""Five sample emails for the simulated inbox.

They are written the way real business email arrives: typos, forwarded threads,
signatures, phone numbers in different formats, budgets mentioned in passing.
All companies, people, addresses and phone numbers are fictional.
"""

from __future__ import annotations

from .models import Message

_EMAILS = [
    {
        "sender": "Dr. Priya Raman <priya@ramandental.example>",
        "subject": "website redo?? + online booking",
        "received": "Mon 9:12 AM",
        "body": """Hi there,

Got your name from Marcus at the chamber meetup. our website is honestly embarassing, it was built in 2016 and doesnt work on phones. We need a full redesign and patients should be able to book appointments online (we use Dentrix if that matters).

Budget is somewhere around $4,500, could stretch a little for the booking part. We open a 2nd location on the 28th so I need this live before then, so pretty urgent on our side.

call me on my cell its easier 415 555 0134

Priya
Raman Family Dental""",
    },
    {
        "sender": "Dev Okafor <dev.okafor@brightlinelogistics.example>",
        "subject": "Re: Re: licenses",
        "received": "Mon 11:47 AM",
        "body": """hey - following up on the call. pls go ahead and add 3 more user licenses to our account + the onboarding training session for the new dispatch team. you said $850 all in, correct?

no big rush, anytime in the next couple weeks works. PO number is BL-2291 if you need it on the paperwork

Dev
Ops Manager, Brightline Logistics
(312) 555-0188

Sent from my iPhone""",
    },
    {
        "sender": "Accounts - Hartwell Bakery <accounts@hartwellbakery.example>",
        "subject": "INVOICE 1047 - query",
        "received": "Tue 8:30 AM",
        "body": """Hello,

Re invoice #1047 dated 3 Nov for the monthly social media management. Amount shows USD 2,350.00 but we agreed 2,100 on the phone?? Can someone confirm and resend the corrected invoice, we'd like to pay it this month.

Regards
Elena Marsh
Hartwell Bakery accounts dept
T: +1 (646) 555-0171""",
    },
    {
        "sender": "tom@peakoutfitters.example",
        "subject": "URGENT - checkout broken!!!",
        "received": "Tue 2:05 PM",
        "body": """Our store checkout has been throwing an error since this morning and customers cant pay. We are losing sales every hour. Need someone on this ASAP, today if at all possible. Whatever it costs, just tell me.

Tom Bradley
Peak Outfitters
720.555.0119""",
    },
    {
        "sender": "Sam Whitlock <sam@yourcompany.example>",
        "subject": "FW: quote request from web form",
        "received": "Wed 10:20 AM",
        "body": """fyi came in through the form over the weekend, can you take this one?

---------- Forwarded message ----------
From: Laura Chen <laura.chen@greenleafyoga.example>
Subject: SEO help

Hi, we're a small yoga studio with 2 locations. Looking for someone to handle our SEO and google business profile on a monthly basis. We can do about $1,200/month. Not urgent at all - planning to start next quarter, just collecting quotes for now.

Laura Chen
Greenleaf Yoga
ph 503-555-0162""",
    },
]


def inbox_rows() -> list[dict]:
    """Sender, subject and time of each sample email, for the inbox table."""
    return [
        # Like a mail client: show the display name, or the bare address when there is none.
        {"From": e["sender"].split(" <")[0], "Subject": e["subject"], "Received": e["received"]}
        for e in _EMAILS
    ]


def sample_messages() -> list[Message]:
    return [
        Message(source=e["subject"], raw=f"From: {e['sender']}\nSubject: {e['subject']}\n\n{e['body']}")
        for e in _EMAILS
    ]
