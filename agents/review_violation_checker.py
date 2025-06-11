from google.adk import Agent
from google.adk.tools.load_web_page import load_web_page
from google.genai import types

from .creatives_agents.tools import check_json_string, export_json_to_dataframe



REVIEW_GUIDELINES = (
"""
What's not allowed
Seller, order, or shipping feedback
We don't allow reviews or questions and answers that focus on:

Sellers and the Customer Service they provide
Ordering issues and returns
Shipping packaging
Product condition and damage
Shipping cost and speed
Why not? Community content is meant to help customers learn about the product itself, not an individual experience ordering it. We definitely want to hear your feedback about sellers and packaging, but not in reviews or questions and answers.

Comments about pricing or availability
If it's related to the value of the product, it's OK to comment on price. For example, For only $29, this blender is really great.

Pricing comments related to an individual experience aren't allowed. For example, Found this item here for $5 less than at my local store.

These comments aren't allowed because they aren't relevant for all customers.

Some comments about availability are OK. For example, I wish this book was also available in paperback.

However, we don't allow comments about availability at a specific store. The purpose of the community is to share product-specific feedback that will be relevant to all other customers.

Content written in unsupported languages
We only allow content to be written in the supported languages of the Amazon site where it will appear. For example, we don't allow reviews written in French on Amazon.com. It only supports English and Spanish. Some Amazon sites support multiple languages, but content written in a mix of languages isn't allowed.

Learn which languages are supported on this Amazon site.

Repetitive text, spam, or pictures created with symbols
We don't allow contributions with distracting content and spam. This restriction includes:

Repetitive text
Nonsense and gibberish
Content that's just punctuation and symbols
ASCII art (pictures created using symbols and letters)
Private information
Don't post content that invades privacy or shares your own personal information, including:

Phone number
Email address
Mailing address
License plate
Data source name (DSN)
Order number
Profanity or harassment
It's OK to question beliefs and expertise, but be respectful. We don't allow:

Profanity, obscenities, or name-calling
Harassment or threats
Attacks on people you disagree with
Libel, defamation, or inflammatory content
Drowning out opinions. Don't post from multiple accounts or coordinate with others.
Hate speech
You are not allowed to express hatred for people based on characteristics like:

Race
Ethnicity
Nationality
Gender
Gender identity
Sexual orientation
Religion
Age
Disability
It's also not allowed to promote organizations that use such hate speech.

Sexual content
It's OK to discuss sex and sensuality products sold on Amazon. The same goes for products with sexual content (books, movies). That said, we still don't allow profanity or obscene language. We also don't allow content with nudity or sexually explicit images or descriptions.

External links
We allow links to other products on Amazon, but not to external sites. Don't post links to phishing or other malware sites. We don't allow URLs with referrer tags or affiliate codes.

Ads, conflicts of interest, promotional content
We don’t allow content if its main purpose is to promote a company, website, author, or special offer. We also don’t allow people to create, edit, or post content about their own products or services. The same goes for products and services offered by:

Friends
Relatives
Employers
Business associates
Competitors
We don't allow reviews written as a form of promotion. We remove reviews posted by someone with financial interest in the product, or any other conflict of interest. See more examples of reviews that we don’t allow.

We don’t allow anyone with a financial or personal connection to the brand, seller, author, or artist to post questions. They can post answers, but only if they clearly and conspicuously disclose their connection. Example: “I represent the brand for this product.” We automatically label some answers from sellers and manufacturers. In that case, additional disclosure is unnecessary.

Excluding reviews and questions and answers, you can post about products to which you are financially or personally connected. It is mandatory, though, that you clearly and conspicuously disclose the connection. Example: “I was paid for this post.” However, brands and businesses can’t participate in the community in ways that divert Amazon customers to non-Amazon environment. That includes advertising, special offers, or "calls to action." Content posted through brand, seller, author, or artist accounts about their own products or services doesn’t need additional labeling.

For details and more examples, read our promotional content guidelines.

Compensated reviews
Reviews should reflect your honest opinion. We don’t allow reviews that are created, edited, or removed in exchange for compensation. Compensation includes cash, discounts, free products, gift cards, and refunds. Some common examples of what’s not allowed:

Your order arrives, and there’s a gift card in the package. To redeem it, you first have to post a positive review.
After leaving a negative review, you get an email offering a refund if you change or remove the review.
You receive a text message that promises full reimbursement for buying a product and posting a review about it.
Exceptions:

We allow reviews of free products received through the Amazon Vine program. We label these reviews with “Vine Customer Review of Free Product.”
It’s OK to review a free or discounted book (advanced reader copy) that you received from an author or publisher. However, they can’t require a review in exchange or try to influence the review.
Plagiarism, infringement, or impersonation
Only post your own content or content that you have permission to use on Amazon. This restriction includes text, images, and videos. You're not allowed to:

Post content that infringes on intellectual property (including copyrights, trademarks, patents, trade secrets) or other proprietary rights
Interact with community members in ways that infringe on intellectual property or proprietary rights
Impersonate someone or an organization
Illegal activities
Don't post content that encourages illegal activity like:

Violence
Illegal drug use
Underage drinking
Child or animal abuse
Fraud
We don't allow content that advocates or threatens physical or financial harm to yourself or others. This restriction includes terrorism. Jokes or sarcastic comments about causing harm aren't allowed.

It's also not allowed to offer fraudulent goods, services, promotions, or schemes (make money fast, pyramid).

You are not allowed to encourage the dangerous misuse of a product.

Medical claims
We don't allow any statements or claims related to preventing or curing serious medical conditions or severe symptoms. This applies to all products, including foods, beverages, supplements, cosmetics, and personal care/general products.

Consequences for violations
Violations of our guidelines make the community less trustworthy, safe, and useful. If someone violates the guidelines, we may:

Remove their content
Limit their ability to use community features
Remove related products
Suspend or terminate their account
Withhold payments
If we find unusual reviewing behavior, we might limit the ability to submit reviews. If we reject or remove your review for guidelines violation, you won't be allowed to review that product again.

If someone violates state and federal laws, including the Federal Trade Commission Act, we might take legal action. This action may result in civil and criminal penalties.

How to report violations
Use the Report link near the content that you want to report.

If someone offers you compensation to create, edit, or remove a review, report it using the Report Review Compensation form.

After we receive your report, we'll investigate and take appropriate action.

To find more information about the Amazon Community and how to contact us, follow these steps:

Visit Customer Service.
Select Help with something else (if this button is displayed).
Select Something else.
Select Amazon Community.
Select the most appropriate option from the list of Amazon Community features.
"""
)


def create_review_violation_checker():
    review_violation_checker_agent = Agent(
        name='amazon_review_violation_checker',
        model='gemini-2.0-flash',
        generate_content_config=types.GenerateContentConfig(max_output_tokens=20000),
        description='An agent who is an expert in assessing customer reviews and checking if the reviews comply with Amazon review community guidelines',
        instruction=f"""You have access to `load_web_page` tool.
        You MUST use it to understand Amazon's review guidelines and policies described here:
        https://www.amazon.com/gp/help/customer/display.html?nodeId=GLHXEX85MENUE4XF
        Use this link to understand the review requirements. If the tool fails, fallback to these review guidelines:
        ----------------------------------------
        REVIEW GUIDELINES.

        {REVIEW_GUIDELINES}
        ----------------------------------------
        """
        """
        Your job is to analyze the submitted reviews thoroughly against the guidelines and return a concise but accurate answer.
        IMPORTANT! Do not flag a review as a violation if it says in some form that the company contacted the buyer and offered a refund.
        Make sure to indicate which part of the review is a violation, and which specific article it violates. Use the following SUBMISSION FORM:

        ----------------------------------------
        ASIN: {the product's ASIN, sometimes the link to Amazon PDP, if provided}
        Title: {the review title, if provided}
        Name of the reviewer: {the author of the review, if provided}
        Date of the review: {the date of the review, if provided}

        Review text: {the text of the review}

        Direct link to the review: {the link to the review, if provided}

        Required action:
        Hi, please remove the following product review because it violates following Amazon's Community Guidelines
        
        Violation: {here you describe which specific part of the review violates a specific article. Please make sure to include the link to the review guidelines}

        ----------------------------------------
        If the review does not violate any guidelines, just confirm it.

        WORKFLOW:

        1. IF the user supplied only texts of the review (not the JSON string from the file):
            1.1 Analyze the review and give the user your output with SUBMISSION FORM
            1.2 Do NOT use the `export_json_to_dataframe`

        2. ELSE IF the user supplied you with multiple texts using a JSON string from a file:
            2.1 Analyze the submitted reviews, but do not output your analysis to the user.
            2.2 For each of the reviews add your analysis results in a "Violation" column of the JSON string.
            2.3 You MUST call `check_json_string` tool to check if the JSON string you created is a valid JSON string, or needs improvements.
                If the tool returns `True`, you are ok to proceed, otherwise please review the sting for errors.
            2.4 You MUST call `export_json_to_dataframe` tool with the updated JSON string. Make sure it's in JSON format.
            2.5 Do NOT output your analysis to the user, instead just inform them that you are using the `export_json_to_dataframe` to generate and download an Excel file.

        """,
        tools=[load_web_page, check_json_string, export_json_to_dataframe]
    )
    return review_violation_checker_agent