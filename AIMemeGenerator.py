
version = "1.0.5"


import openai
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from PIL import Image, ImageDraw, ImageFont
import requests
import httpx



import warnings
import re
from base64 import b64decode
from pkg_resources import parse_version
from collections import namedtuple
import io
from datetime import datetime
import glob
import string
import os
import textwrap
import sys
import argparse
import configparser
import platform
import shutil
import traceback



parser = argparse.ArgumentParser()
parser.add_argument("--openaikey", help="OpenAI API key")
parser.add_argument("--clipdropkey", help="ClipDrop API key")
parser.add_argument("--stabilitykey", help="Stability AI API key")
parser.add_argument("--userprompt", help="A meme subject or concept to send to the chat bot. If not specified, the user will be prompted to enter a subject or concept.")
parser.add_argument("--memecount", help="The number of memes to create. If using arguments and not specified, the default is 1.")
parser.add_argument("--imageplatform", help="The image platform to use. If using arguments and not specified, the default is 'clipdrop'. Possible options: 'openai', 'stability', 'clipdrop'")
parser.add_argument("--temperature", help="The temperature to use for the chat bot. If using arguments and not specified, the default is 1.0")
parser.add_argument("--basicinstructions", help=f"The basic instructions to use for the chat bot. If using arguments and not specified, default will be used.")
parser.add_argument("--imagespecialinstructions", help=f"The image special instructions to use for the chat bot. If using arguments and not specified, default will be used")

parser.add_argument("--nouserinput", action='store_true', help="Will prevent any user input prompts, and will instead use default values or other arguments.")
parser.add_argument("--nofilesave", action='store_true', help="If specified, the meme will not be saved to a file, and only returned as virtual file part of memeResultsDictsList.")
args = parser.parse_args()


ApiKeysTupleClass = namedtuple('ApiKeysTupleClass', ['openai_key', 'clipdrop_key', 'stability_key'])


class NoFontFileError(Exception):
    def __init__(self, message, font_file):
        full_error_message = f'Font file "{font_file}" not found. Please add the font file to the same folder as this script. Or set the variable above to the name of a font file in the system font folder.'
        
        super().__init__(full_error_message)
        self.font_file = font_file
        self.simple_message = message
        
class MissingOpenAIKeyError(Exception):
    def __init__(self, message):
        full_error_message = f"No OpenAI API key found. OpenAI API key is required - In order to generate text for the meme text and image prompt. Please add your OpenAI API key to the api_keys.ini file."
        
        super().__init__(full_error_message)
        self.simple_message = message    
        
class MissingAPIKeyError(Exception):
    def __init__(self, message, api_platform):
        full_error_message = f"{api_platform} was set as the image platform, but no {api_platform} API key was found in the api_keys.ini file."
        
        super().__init__(full_error_message)
        self.api_platform = api_platform
        self.simple_message = message

class InvalidImagePlatformError(Exception):
    def __init__(self, message, given_platform, valid_platforms):
        full_error_message = f"Invalid image platform '{given_platform}'. Valid image platforms are: {valid_platforms}"
        
        super().__init__(full_error_message)
        self.given_platform = given_platform
        self.valid_platforms = valid_platforms
        self.simple_message = message




def construct_system_prompt(basic_instructions, image_special_instructions):
    format_instructions = f'You are a meme generator with the following formatting instructions. Each meme will consist of text that will appear at the top, and an image to go along with it. The user will send you a message with a general theme or concept on which you will base the meme. The user may choose to send you a text saying something like "anything" or "whatever you want", or even no text at all, which you should not take literally, but take to mean they wish for you to come up with something yourself.  The memes don\'t necessarily need to start with "when", but they can. In any case, you will respond with two things: First, the text of the meme that will be displayed in the final meme. Second, some text that will be used as an image prompt for an AI image generator to generate an image to also be used as part of the meme. You must respond only in the format as described next, because your response will be parsed, so it is important it conforms to the format. The first line of your response should be: "Meme Text: " followed by the meme text. The second line of your response should be: "Image Prompt: " followed by the image prompt text.  --- Now here are additional instructions... '
    basicInstructionAppend = f'Next are instructions for the overall approach you should take to creating the memes. Interpret as best as possible: {basic_instructions} | '
    specialInstructionsAppend = f'Next are any special instructions for the image prompt. For example, if the instructions are "the images should be photographic style", your prompt may append ", photograph" at the end, or begin with "photograph of". It does not have to literally match the instruction but interpret as best as possible: {image_special_instructions}'
    systemPrompt = format_instructions + basicInstructionAppend + specialInstructionsAppend
    
    return systemPrompt




def check_font(font_file):
    
    if not os.path.isfile(font_file):
        if platform.system() == "Windows":
            
            font_file = os.path.join(os.environ['WINDIR'], 'Fonts', font_file)
        elif platform.system() == "Linux":
            
            font_directories = ["/usr/share/fonts", "~/.fonts", "~/.local/share/fonts", "/usr/local/share/fonts"]
            found = False
            for dir in font_directories:
                dir = os.path.expanduser(dir)
                for root, dirs, files in os.walk(dir):
                    if font_file in files:
                        font_file = os.path.join(root, font_file)
                        found = True
                        break
      
                if found:
                    break

        
        if not os.path.isfile(font_file):
            raise NoFontFileError(f'Font file "{font_file}" not found.', font_file)
        
    
    return font_file

def parseBool(string, silent=False):
    if type(string) == str:
        if string.lower() == 'true':
            return True
        elif string.lower() == 'false':
            return False
        else:
            if not silent:
                raise ValueError(f'Invalid value "{string}". Must be "True" or "False"')
            elif silent:
                return string
    elif type(string) == bool:
        if string == True:
            return True
        elif string == False:
            return False
    else:
        raise ValueError('Not a valid boolean string')


def get_config(config_file_path):
    config_raw = configparser.ConfigParser()
    config_raw.optionxform = lambda option: option  
    config_raw.read(config_file_path, encoding='utf-8')

  
    config = {}
    for section in config_raw.sections():
        for key in config_raw[section]:
            settingValue = config_raw[section][key]
            
            settingValue = settingValue.strip("\"").strip("\'")
           
            if type(parseBool(settingValue, silent=True)) == bool:
                settingValue = parseBool(settingValue)
            config[key] = settingValue  

    return config

def get_assets_file(fileName):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, fileName)
    return os.path.join(os.path.abspath("assets"), fileName) 


def get_settings(settings_filename="settings.ini"):
    default_settings_filename = "settings_default.ini"
    def check_settings_file():
        if not os.path.isfile(settings_filename):
            file_to_copy_path = get_assets_file(default_settings_filename)
            shutil.copyfile(file_to_copy_path, settings_filename)
            print("\nINFO: Settings file not found, so default 'settings.ini' file created. You can use it going forward to change more advanced settings if you want.")
            input("\nPress Enter to continue...")
    
    check_settings_file()
    
    try:
        settings = get_config(settings_filename)
        pass
    except:
        settings = get_config(get_assets_file(default_settings_filename))
        print("\nERROR: Could not read settings file. Using default settings instead.")
        
    
    if settings == {}:
        settings = get_config(get_assets_file(default_settings_filename))
        print("\nERROR: Something went wrong reading the settings file. Using default settings instead.")
        
    return settings


def get_api_keys(api_key_filename="api_keys.ini", args=None):
    default_api_key_filename = "api_keys_empty.ini"
    
    
    def check_api_key_file():
        if not os.path.isfile(api_key_filename):
            file_to_copy_path = get_assets_file(default_api_key_filename)
            
            shutil.copyfile(file_to_copy_path, api_key_filename)
            print(f'\n  INFO:  Because running for the first time, "{api_key_filename}" was created. Please add your API keys to the API Keys file.')
            input("\nPress Enter to exit...")
            sys.exit()

    
    check_api_key_file()
    
   
    openai_key, clipdrop_key, stability_key = '', '', ''

   
    try:
        keys_dict = get_config(api_key_filename)
        openai_key = keys_dict.get('OpenAI', '')
        clipdrop_key = keys_dict.get('ClipDrop', '')
        stability_key = keys_dict.get('StabilityAI', '')
    except FileNotFoundError:
        print("Config not found, checking for command line arguments.")  

   
    if not all(value is None for value in vars(args).values()):
        openai_key = args.openaikey if args.openaikey else openai_key
        clipdrop_key = args.clipdropkey if args.clipdropkey else clipdrop_key
        stability_key = args.stabilitykey if args.stabilitykey else stability_key

    return ApiKeysTupleClass(openai_key, clipdrop_key, stability_key)


def validate_api_keys(apiKeys, image_platform):
    if not apiKeys.openai_key:
        raise MissingOpenAIKeyError("No OpenAI API key found.")

    valid_image_platforms = ["openai", "stability", "clipdrop"]
    image_platform = image_platform.lower()

    if image_platform in valid_image_platforms:
        if image_platform == "stability" and not apiKeys.stability_key:
            raise MissingAPIKeyError("No Stability AI API key found.", "Stability AI")

        if image_platform == "clipdrop" and not apiKeys.clipdrop_key:
            raise MissingAPIKeyError("No ClipDrop API key found.", "ClipDrop")

    else:
        raise InvalidImagePlatformError(f'Invalid image platform provided.', image_platform, valid_image_platforms)

def initialize_api_clients(apiKeys, image_platform):
    if apiKeys.openai_key:
        openai_api = openai.OpenAI(api_key=apiKeys.openai_key, http_client=httpx.Client())


    if apiKeys.stability_key and image_platform == "stability":
        stability_api = client.StabilityInference(
            key=apiKeys.stability_key,
            verbose=True, 
            engine="stable-diffusion-xl-1024-v0-9", 
            )
    else:
        stability_api = None
    
    
    return stability_api, openai_api



def set_file_path(baseName, outputFolder):
    def get_next_counter():
        
        existing_files = glob.glob(os.path.join(outputFolder, baseName + "_" + timestamp + "_*.png"))

       
        max_counter = 0
        for file in existing_files:
            try:
                counter = int(os.path.basename(file).split('_')[-1].split('.')[0])
                max_counter = max(max_counter, counter)
            except ValueError:
                pass
        
        return max_counter + 1

    
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    

    if not os.path.exists(outputFolder):
        os.makedirs(outputFolder)
    
    
    file_counter = get_next_counter()

    
    fileName = baseName + "_" + timestamp + "_" + str(file_counter) + ".png"
    filePath = os.path.join(outputFolder, fileName)
    
    return filePath, fileName

    

def write_log_file(userPrompt, AiMemeDict, filePath, logFolder, basic, special, platform):
    # Get file name from path
    memeFileName = os.path.basename(filePath)
    with open(os.path.join(logFolder, "log.txt"), "a", encoding='utf-8') as log_file:
        log_file.write(textwrap.dedent(f"""
                       Meme File Name: {memeFileName}
                       AI Basic Instructions: {basic}
                       AI Special Image Instructions: {special}
                       User Prompt: '{userPrompt}'
                       Chat Bot Meme Text: {AiMemeDict['meme_text']}
                       Chat Bot Image Prompt: {AiMemeDict['image_prompt']}
                       Image Generation Platform: {platform}
                       \n"""))


def parse_meme(message):
    
    pattern = r'Meme Text: (\"(.*?)\"|(.*?))\n*\s*Image Prompt: (.*?)$'

    match = re.search(pattern, message, re.DOTALL)

    if match:
        
        meme_text = match.group(2) if match.group(2) is not None else match.group(3)
        
        return {
            "meme_text": meme_text,
            "image_prompt": match.group(4)
        }
    else:
        return None
    

def send_and_receive_message(openai_api, text_model, userMessage, conversationTemp, temperature=0.5):
    
    conversationTemp.append({"role": "user", "content": userMessage})
    
    print("Sending request to write meme...")
    chatResponse = openai_api.chat.completions.create(
        model=text_model,
        messages=conversationTemp,
        temperature=temperature
        )

    chatResponseMessage = chatResponse.choices[0].message.content
    chatResponseRole = chatResponse.choices[0].message.role

    return chatResponseMessage


def create_meme(image_path, top_text, filePath, fontFile, noFileSave=False, min_scale=0.05, buffer_scale=0.03, font_scale=1):
    print("Creating meme image...")
    
   
    image = Image.open(image_path)

  
    buffer_size = int(buffer_scale * image.width)

  
    d = ImageDraw.Draw(image)

    
    words = top_text.split()

   
    font_size = int(font_scale * image.width)
    fnt = ImageFont.truetype(fontFile, font_size)
    wrapped_text = top_text

    
    while d.textbbox((0,0), wrapped_text, font=fnt)[2] > image.width - 2 * buffer_size:
        font_size *= 0.9  
        if font_size < min_scale * image.width:
            
            lines = [words[0]]
            for word in words[1:]:
                new_line = (lines[-1] + ' ' + word).rstrip()
                if d.textbbox((0,0), new_line, font=fnt)[2] > image.width - 2 * buffer_size:
                    lines.append(word)
                else:
                    lines[-1] = new_line
            wrapped_text = '\n'.join(lines)
            break
        fnt = ImageFont.truetype(fontFile, int(font_size))

 
    textbbox_val = d.multiline_textbbox((0,0), wrapped_text, font=fnt)

    
    band_height = textbbox_val[3] - textbbox_val[1] + int(font_size * 0.1) + 2 * buffer_size
    band = Image.new('RGBA', (image.width, band_height), (255,255,255,255))

   
    d = ImageDraw.Draw(band)

  
    text_x = band.width // 2 
    text_y = band.height // 2

    d.multiline_text((text_x, text_y), wrapped_text, font=fnt, fill=(0,0,0,255), anchor="mm", align="center")

    
    new_img = Image.new('RGBA', (image.width, image.height + band_height))
    new_img.paste(band, (0,0))
    new_img.paste(image, (0, band_height))

    if not noFileSave:
      
        new_img.save(filePath)
        
    
    virtualMemeFile = io.BytesIO()
    new_img.save(virtualMemeFile, format="PNG")
    
    return virtualMemeFile
    

def image_generation_request(apiKeys, image_prompt, platform, openai_api, stability_api=None):
    if platform == "openai":
        openai_response = openai_api.images.generate(model="dall-e-3", prompt=image_prompt, n=1, size="1024x1024", response_format="b64_json")
       
        image_data = b64decode(openai_response.data[0].model_dump()["b64_json"])
        virtual_image_file = io.BytesIO()
       
        virtual_image_file.write(image_data)
    
    if platform == "stability" and stability_api:
        
        stability_response = stability_api.generate(
            prompt=image_prompt,
            #seed=992446758, 
            steps=30,       
            cfg_scale=7.0,  
            width=1024, 
            height=1024, 
            samples=1,
            sampler=generation.SAMPLER_K_DPMPP_2M  
                                                   )

       
        for resp in stability_response:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    warnings.warn(
                        "Your request activated the API's safety filters and could not be processed."
                        "Please modify the prompt and try again.")
                if artifact.type == generation.ARTIFACT_IMAGE:
                    
                    virtual_image_file = io.BytesIO(artifact.binary)

    if platform == "clipdrop":
        r = requests.post('https://clipdrop-api.co/text-to-image/v1',
            files = {
                'prompt': (None, image_prompt, 'text/plain')
            },
            headers = { 'x-api-key': apiKeys.clipdrop_key}
        )
        if (r.ok):
            virtual_image_file = io.BytesIO(r.content) # r.content contains the bytes of the returned image
        else:
            r.raise_for_status()

    return virtual_image_file

def generate(
    text_model="gpt-4",
    temperature=1.0,
    basic_instructions=r'You will create funny memes that are clever and original, and not cliche or lame.',
    image_special_instructions=r'The images should be photographic.',
    user_entered_prompt="anything",
    meme_count=1,
    image_platform="openai",
    font_file="arial.ttf",
    base_file_name="meme",
    output_folder="Outputs",
    openai_key=None,
    stability_key=None,
    clipdrop_key=None,
    noUserInput=False,
    noFileSave=False,
    release_channel="all"
):
    
    
    settings = get_settings()
    use_config = settings.get('Use_This_Config', False) 
    if use_config:
        text_model = settings.get('Text_Model', text_model)
        temperature = float(settings.get('Temperature', temperature))
        basic_instructions = settings.get('Basic_Instructions', basic_instructions)
        image_special_instructions = settings.get('Image_Special_Instructions', image_special_instructions)
        image_platform = settings.get('Image_Platform', image_platform)
        font_file = settings.get('Font_File', font_file)
        base_file_name = settings.get('Base_File_Name', base_file_name)
        output_folder = settings.get('Output_Folder', output_folder)
        release_channel = settings.get('Release_Channel', release_channel)
    
   
    args = parser.parse_args()

   
    if not openai_key:
        apiKeys = get_api_keys(args=args)
    else:
        apiKeys = ApiKeysTupleClass(openai_key, clipdrop_key, stability_key)
        
    
    validate_api_keys(apiKeys, image_platform)
   
    stability_api, openai_api = initialize_api_clients(apiKeys, image_platform)

    
    if args.imageplatform:
        image_platform = args.imageplatform
    if args.temperature:
        temperature = float(args.temperature)
    if args.basicinstructions:
        basic_instructions = args.basicinstructions
    if args.imagespecialinstructions:
        image_special_instructions = args.imagespecialinstructions
    if args.nofilesave:
        noFileSave=True
    if args.nouserinput:
        noUserInput=True

    systemPrompt = construct_system_prompt(basic_instructions, image_special_instructions)
    conversation = [{"role": "system", "content": systemPrompt}]

    
    try:
        font_file = check_font(font_file)
    except NoFontFileError as fx:
        print(f"\n  ERROR:  {fx}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
                
    
    os.system('cls' if os.name == 'nt' else 'clear')

   
    print(f"\n==================== AI Meme Generator - {version} ====================")

    if noUserInput:
        userEnteredPrompt = user_entered_prompt
        meme_count = meme_count 
    
    
    else:
        
        if not args.userprompt:
            print("\nEnter a meme subject or concept (Or just hit enter to let the AI decide)")
            userEnteredPrompt = input(" >  ")
            if not userEnteredPrompt: 
                userEnteredPrompt = "anything"
        else:
            userEnteredPrompt = args.userprompt
        
        
        if not args.memecount:
            
            meme_count = 1
            print("\nEnter the number of memes to create (Or just hit Enter for 1): ")
            userEnteredCount = input(" >  ")
            if userEnteredCount:
                meme_count = int(userEnteredCount)
        else:
            meme_count = int(args.memecount)
            
    

    def single_meme_generation_loop():
        
        chatResponse = send_and_receive_message(openai_api, text_model, userEnteredPrompt, conversation, temperature)

       
        memeDict = parse_meme(chatResponse)
        image_prompt = memeDict['image_prompt']
        meme_text = memeDict['meme_text']

        
        print("\n   Meme Text:  " + meme_text)
        print("   Image Prompt:  " + image_prompt)

        
        print("\nSending image creation request...")
        virtual_image_file = image_generation_request(apiKeys, image_prompt, image_platform, openai_api, stability_api)

        
        filePath,fileName = set_file_path(base_file_name, output_folder)
        virtualMemeFile = create_meme(virtual_image_file, meme_text, filePath, noFileSave=noFileSave,fontFile=font_file)
        if not noFileSave:
            
            write_log_file(userEnteredPrompt, memeDict, filePath, output_folder, basic_instructions, image_special_instructions, image_platform)
        
        absoluteFilePath = os.path.abspath(filePath)
        
        return {"meme_text": meme_text, "image_prompt": image_prompt, "file_path": absoluteFilePath, "virtual_meme_file": virtualMemeFile, "file_name": fileName}
    
  
    memeResultsDictsList = []

   
    try:
        
        for i in range(meme_count):
            print("\n----------------------------------------------------------------------------------------------------")
            print(f"Generating meme {i+1} of {meme_count}...")
            memeInfoDict = single_meme_generation_loop()

           
            memeResultsDictsList.append(memeInfoDict)
            
        
        print("\n\nFinished. Output directory: " + os.path.abspath(output_folder))
        if not noUserInput:
            input("\nPress Enter to exit...")
    
    except MissingOpenAIKeyError as ox:
        print(f"\n  ERROR:  {ox}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
        
    except MissingAPIKeyError as ax:
        print(f"\n  ERROR:  {ax}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
        
 
    except openai.NotFoundError as nfx:
        print(f"\n  ERROR:  {nfx}")
        if "The model" in str(nfx) and "does not exist" in str(nfx):
            #if 'gpt-4' in str(irx):
            if str(nfx) == "The model `gpt-4` does not exist":
                print("  (!) Note: This error actually means you do not have access to the GPT-4 model yet.")
                print("  (!)       - You can see more about the current GPT-4 requirements here: https://help.openai.com/en/articles/7102672-how-can-i-access-gpt-4")
                print("  (!)       - Also ensure your country is supported: https://platform.openai.com/docs/supported-countries")
                print("  (!)       - You can try the 'gpt-3.5-turbo' model instead. See more here: https://platform.openai.com/docs/models/overview)")
            else:
                print("   > Either the model name is incorrect, or you do not have access to it.")
                print("   > See this page to see the model names to use in the API: https://platform.openai.com/docs/models/overview")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
    
    except Exception as ex:
        
        traceback.print_exc()
        print(f"\n  ERROR:  An error occurred while generating the meme. Error: {ex}")
        if not noUserInput:
            input("\nPress Enter to exit...")
        sys.exit()
    
  
    return memeResultsDictsList

if __name__ == "__main__":
    generate()
