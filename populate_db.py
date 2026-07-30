from core.database import Database

db = Database()

# 1. Add Settings
settings = {
    "gemini_api_key": "AQ.Ab8RN6KPpujA7cz3vmqjKCQRhbrmQVDS_c4EmDH_BLPOThkhvw",
    "telegram_bot_token": "8878942621:AAEUNJJ1mOuMrCy4idWlhGuV2YKRXIdDwec",
    "telegram_chat_id": "8048760547",
    "headless_mode": "Yes",
    "subreddits": "shamelessplug, SaaS_Promotions, startups_promotion, IMadeThis, AlphaandBetausers, selfpromotion, SideProject, coolgithubprojects, EntrepreneurRideAlong, indiehackers, smallbusiness, startups, Entrepreneur, SaaS, marketing, digital_marketing, SEO, content_marketing, socialmedia, VideoEditing, VideoProfessionals, YouTubers, podcasting, audioproduction, writing, selfpublish, WritersGroup, freelance, freelanceWriters, copywriting, GraphicDesign, Design, photography, Art, StableDiffusion, midjourney, ArtificialInteligence, MachineLearning, webdev, programming, devops, sysadmin, productivity, solopreneurs, ecommerce, shopify, dropship, juststart, Beermoney, Automate, DigitalMarketing, Blogging, ChatGPTPro, GPTStore, aipromptengineering, ChatGPTCoding, AutoGPT, LocalGPT"
}

for k, v in settings.items():
    db.save_setting(k, v)

# 2. Add a Tool
db.add_tool(
    name="DZ-GHOST AI Bot",
    description="An automated Reddit marketing bot that finds leads and writes comments.",
    affiliate_link="https://example.com/dz-ghost"
)

print("Database successfully populated!")
