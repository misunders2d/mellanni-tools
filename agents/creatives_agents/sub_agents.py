from google.adk.agents import Agent, LoopAgent
from google.adk.tools import google_search, load_web_page
from .tools import exit_loop
from . import prompts

from data import CREATIVES_AGENT_MODEL


#--- checker agent creating functions
def create_fact_checker(name=prompts.FACT_CHECKER_AGENT):
    fact_checker_agent = Agent(
        name=name,
        model=CREATIVES_AGENT_MODEL,
        description='An agent meticulously checking facts from a given text. Uses web search to search for information',
        instruction=prompts.FACT_CHECK_AGENT_INSTRUCTIONS,
        tools=[google_search],
        output_key='fact_checker_corrections'
    )
    return fact_checker_agent

def create_image_prompt_checker(name=prompts.IMAGE_PROMPTS_CHECKER):
    image_prompt_checker_agent = Agent(
        name=name,
        model=CREATIVES_AGENT_MODEL,
        description='An agent who is an expert in image generation and can check presented prompts for inconsistencies or flaws, and suggest improvements',
        instruction=prompts.IMAGE_PROMPT_CHECKER_INSTRUCTIONS,
        output_key='image_prompt_checker_corrections'
    )
    return image_prompt_checker_agent

#--- storyline 
storyline_agent = Agent(
    name='storyline_generator',
    model=CREATIVES_AGENT_MODEL,
    # model=LiteLlm('openai/gpt-4o-mini', api_key=os.environ['OPENAI_API_KEY']),
    description='An agent generating engaging storylines from a given topic. The storylines are suitable for various social media platforms',
    instruction=prompts.STORYLINE_AGENT_INSTRUCTIONS,
    tools=[exit_loop],
    output_key=prompts.INITIAL_STORYLINES,
)


storyline_loop_agent = LoopAgent(
    name=prompts.STORYLINE_AGENT,
    description='An agent that creates storylines and checks facts in this content using google search',
    sub_agents=[storyline_agent, create_fact_checker(name=prompts.FACT_CHECKER_AGENT)],
    max_iterations=7
)

#--- full content
full_content_drafter_agent = Agent(
    name='full_content_drafter',
    model=CREATIVES_AGENT_MODEL,
    description='An agent who creates expanded content based on the provided storyline',
    instruction=prompts.FULL_CONTENT_AGENT_INSTRUCTIONS,
    tools=[exit_loop],
    output_key=prompts.CAPTIONS_TEXT
)

full_content_loop_agent = LoopAgent(
    name=prompts.CONTENT_CREATOR,
    description='An agent that creates captions based on the approved storyline and checks facts in this content using google search',
    sub_agents=[full_content_drafter_agent, create_fact_checker(name=prompts.FACT_CHECKER_AGENT)],
    max_iterations=7
)

#--- image generation
image_prompt_generator_agent = Agent(
    name='image_prompt_generator',
    model=CREATIVES_AGENT_MODEL,
    description='An agent who creates rich, detailed prompts for image generation',# and creates images using `create_vertexai_image` tool',
    instruction=prompts.IMAGE_PROMPT_AGENT_INSTRUCTIONS,
    tools=[exit_loop],
    output_key=prompts.IMAGE_PROMPT
)

image_prompt_loop_agent = LoopAgent(
    name=prompts.IMAGE_PROMPTS_CREATOR,
    description='An agent that creates rich image-generation prompts',
    sub_agents=[image_prompt_generator_agent, create_image_prompt_checker(name=prompts.IMAGE_PROMPTS_CHECKER)],
    max_iterations=7
)

video_generation_drafter=Agent(
    name='video_prompts_drafter_agent',
    description='An agent which drafts prompts for video generation models',
    instruction=prompts.VIDEO_GENERATION_GUIDELINES,
    tools=[exit_loop],
    output_key=prompts.VIDEO_PROMPTS
)

video_prompt_checker=Agent(
    name=prompts.VIDEO_PROMPTS_CHECKER,
    description='An agent who is an expert in video prompts and checsk the submitted prompts for errors and completeness',
    instruction=prompts.VIDEO_PROMPT_CHECKER_INSTRUCTIONS,
    tools=[load_web_page.load_web_page]
)

video_generator_loop_agent = LoopAgent(
    name=prompts.VIDEO_PROMPTS_CREATOR,
    description='An agent that creates rich video-generation prompts',
    sub_agents=[video_generation_drafter, video_prompt_checker],
    max_iterations=7
)