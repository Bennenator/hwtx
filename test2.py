import streamlit as st
import random
from pymongo import MongoClient
import copy
import bcrypt

#Must be the first code to run for the formatting
st.set_page_config(
    page_title="DND Creator",
    page_icon="\U0001F3B2",
    layout="wide")
    
#Adds an image as a background (Good lord, would have been easier without)
#Needed to reference the dev tools on Google to get rid of the header and make the image take the whole screen
#Source: https://github.com/streamlit/streamlit/issues/3073
page_bg_img = '''
<style>
.stApp {
  background-image: url("https://www.tribality.com/wp-content/uploads/2019/07/andreas-rocha-fieldsofgold011-750x375.jpg");
  background-size: cover;
}
[data-testid="stHeader"] {
background-color: rgba(0, 0, 0, 0);
}
</style>
'''
st.markdown(page_bg_img, unsafe_allow_html=True)

# Connect to the MongoDB server
uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"

# Custom HTML and CSS to style any text that is passed to writeCool()
html_code = """
<style>
  .custom-text {
    background-color: beige;
    font-color: black;
    border: 1px solid gray;
    padding: 10px;
    border-radius: 5px;
  }
</style>
<span class="custom-text">"""

html_code2 = """</span>
"""

outlined_text_style = """
<style>
  .outlined-text {
    font-weight: bold;
    font-size: 24px;
    color: beige;
    -webkit-text-stroke: 1px grey;
  }
</style>
<span class="outlined-text">"""

outlined_text_styleB = """
<style>
  .pink-text {
    font-weight: bold;
    font-size: 32px;
    color: pink;
    -webkit-text-stroke: 1px grey;
  }
</style>
<span class="pink-text">"""

outlined_text_style2 = """</span>
"""

def writeCool(home, text, option = 1):
    if option == 1:
        home.markdown(html_code+str(text)+html_code2, unsafe_allow_html=True)
    elif option == 2:
        home.markdown(outlined_text_style+str(text)+outlined_text_style2, unsafe_allow_html=True)
    elif option == 3:
        home.markdown(outlined_text_styleB+str(text)+outlined_text_style2, unsafe_allow_html=True)


# Initial conditions of session states that must be preserved
if "registering" not in st.session_state:
    st.session_state.registering = False
if "loggedIn" not in st.session_state:
    st.session_state.loggedIn = False
if "Username" not in st.session_state:
    st.session_state.Username = None
if "SelectedCharacterID" not in st.session_state:
    st.session_state.SelectedCharacterID = None
if "editing" not in st.session_state:
    st.session_state.editing = False
if "changes" not in st.session_state:
    st.session_state.changes = {}
if "PageNum" not in st.session_state:
    st.session_state.PageNum = 0

# Initialize the mongodb client
client = MongoClient(uri)

# Access the database and subcollections that handle storage of characters and logins
db = client["mydatabase"]
login_info = db["login_info"]
charactersdb = db["character_info10"]

# Streamlit title
writeCool(st, "Gamemaster's Mythical Mind", 2)

# This function takes in username and password strings, checks if they exist, and then authenticates the 
# input username and password
def UserLogin(username, password):
    if not username:
        return "Please enter a username", 0
    if not password:
        return "Please enter a password", 0
    
    account = list(login_info.find({"username": username}))[0] if list(login_info.find({"username": username})) else None
    if not account:
        return "Username not found", 0
    
    if bcrypt.checkpw(password.encode('utf-8'), account["password"]):
        st.session_state.loggedIn = True
        st.session_state.Username = username
        return "Log in successfull!", account["_id"]
    else:
        return "Password is invalid :(", 0
        
# This function takes in username, password, and confirmpassword strings, verifies several axoms that usernames and passwords
# must follow, and if found valid the account is created
def registerUser(username, password, confirmpassword):
    if not username:
        return "Please enter a username", 0
    if not password:
        return "Please enter a password", 0
    if password != confirmpassword:
        return "Passwords must match", 0
        
    if login_info.count_documents({"username":username}) > 0:
        return "Username taken", 0
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    login_info.insert_one({"username": username, "password": hashed_password})
    st.session_state.registering = False
    return "Registration successfull!", 1

# The following 3 helper functions are used in conjunction with buttons to serve as callback functions to update
# certain session states immediately prior to streamlit reruns (updates).
def setRegistering(isregistering):
    st.session_state.registering = isregistering

def setEditing(isEditing):
    st.session_state.editing = isEditing
    
def logOut():
    st.session_state.loggedIn = False

def goPageOne():
    st.session_state.PageNum = 1
    
# This function handles new character database entries and only takes in the username to which the character is
# to be bound and the name of the character to doubly serve as a unique ID.
def createCharacter(username, name):
    if name:
        characters = list(charactersdb.find({"owner":username}))
        for character in characters:
            if character["data"]["name"] == name:
                return "Name taken", 0
        base_character = charactersdb.find_one({"owner":1})
        base_character["data"]["name"] = name
        charactersdb.insert_one({"owner":st.session_state.Username, "data": base_character["data"]})
        return "Character created!", 1

# saveCharacter takes a character object (dictionary) and a changes object (also dictionary) as inputs and
# checks which (if any) of the values within the input character object needs to be updated. Then, the existence
# of the character is checked within the database of characters, and if found to exist the character is updated
# and saved to the database
def saveCharacter(character, changes):
    for key, value in changes.items():
        if key in character["data"].keys():
            character["data"][key] = value
    existing_character = charactersdb.find_one({"_id":character["_id"]})
    if existing_character:
        charactersdb.update_one({"_id": existing_character["_id"]}, {"$set": character})
        return f"{character['data']['name']} saved!"
    else:
        return "Character not found :("

# Changing between scenes in Gamemaster's Mythical Mind is handled by dynamic checking of session states,
# which are preserved through streamlit reruns (updates). The main logic of this large if-else statement is
# designed to display the page correctly after logging in or logging out.
if st.session_state.loggedIn == True:
    # The logged in page is handled within this block
    
    #characters is the list of character objects that have an "owner" attribute of the current logged in User.
    characters = list(charactersdb.find({"owner":st.session_state.Username}))
    chosen_character = {"data":{}}
    
    # This with structure is how streamlit likes to handle the sidebar object. In this case, the sidebar is 
    # designed to handle account management, character creation, and character selection.
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.Username}")
        st.button("Logout", on_click=logOut)
        
        # This with structure is how streamlit likes to handle form objects. Forms are neatly contained elements
        # ALWAYS with a single submit button and no other buttons.
        with st.form("Create a new character"):
            namefieldcol, namebcol = st.columns([7,3])
            namefield = namefieldcol.text_input("Enter new name")
            namebutton = namebcol.form_submit_button("Create")
            
            # If the button labeled "Create" is pressed, it calls createCharacter with the current User and
            # the current value within namefield as arguments. Then, it displays the success message and, if
            # successfull, the streamlit app is manually reran to update the page properly.
            if namebutton:
                tryCreate = createCharacter(st.session_state.Username, namefield)
                st.write(tryCreate[0])
                if tryCreate[1]:
                    st.session_state.PageNum = 1
                    st.experimental_rerun()
        
        # The selectbox can only reasonably contain the names of the characters, so here (unfortunately) a linear search
        # is done after selecting the name of the chosen character to display in order to actually return the character object
        chosen_character_name = st.selectbox("Select a character", [character["data"]["name"] for character in characters], on_change=goPageOne)
        for character in characters:
            if character["data"]["name"] == chosen_character_name:
                chosen_character = character
        if st.session_state.PageNum == 0 and characters:
            st.session_state.PageNum = 1
            st.experimental_rerun()
    
    # This is similar to the outer if-else statement in that it is used to control what elements are being displayed
    # based upon (in this case) the "editing" session state. "editing" is solely an indicator as to whether or not
    # the current character is being edited.
    if st.session_state.editing:
        # Currently being edited block
        
        # This sets up the columns for the main display of the character information and editing buttons.
        charcol1, charcol2 = st.columns([4,6])
        subcol1, subcol2 = charcol1.columns(2)
        
        # If the button labeled "save" is pressed, it calls saveCharacter with the listed args and then updates
        # the relevant session states and reruns streamlit to display the correct state of the page
        if subcol1.button("save", on_click=saveCharacter, args = [chosen_character, st.session_state.changes]):
            st.session_state.editing = False
            st.session_state.changes = {}
            st.experimental_rerun()
            
        if subcol2.button("cancel"):
            st.session_state.changes = {}
            st.session_state.editing = False
            st.experimental_rerun()
        
        # This is the main display driver for the selected character's information. It loops through each
        # key-value pair within the chosen character's "data" attribute and displays an editable text field
        # with a label of whatever attribute it is and an initial value of whatever the value already was.
        # Then, when the submit button is pressed, the session state of "changes" (dictionary) receives a new
        # key value pair of whatever the change was and to what was changed. This means that values are only 
        # "locked in" when the submit button is pressed.
        for key, dict_value in chosen_character["data"].items():
            with charcol1.form(key):
                writeCool(st, key, 2)
                new_entry = st.text_input(key, value=dict_value, label_visibility="collapsed")
                submitbutton = st.form_submit_button("submit")
                if submitbutton:
                    st.session_state.changes[key] = new_entry
    else:
        # Currently not being edited block
        #Changing the page based off position
        button_columns = st.columns([.2,.25,.1,.25,.2])
        if st.session_state.PageNum > 1:
            if button_columns[0].button("Previous Page"):
                st.session_state.PageNum -= 1
                st.experimental_rerun()
        if st.session_state.PageNum <= 3 and st.session_state.PageNum > 0:
            if button_columns[4].button("Next Page"):
                st.session_state.PageNum += 1
                st.experimental_rerun()
        button_columns[2].button("Edit", on_click=setEditing, args=[True])
        #Character Details Page
        if st.session_state.PageNum == 1:
        
            main_cols = st.columns(2)
            name_column, level_column= main_cols[1].columns([0.5,0.5])
            class_column, current_XP_column = main_cols[1].columns([0.5,0.5])
            race_column, next_XP_column = main_cols[1].columns([0.5,0.5])
            bonusXP_column, notes_column = main_cols[1].columns([0.5,0.5])
            
            
            name = chosen_character["data"]["name"]
            level = chosen_character["data"]["level"]
            occupation = chosen_character["data"]["class"]
            race = chosen_character["data"]["race"]
            cxp = chosen_character["data"]["currentXP"]
            nxp = chosen_character["data"]["nextXP"]
            bxp = chosen_character["data"]["xpBonus"]
            notes = chosen_character["data"]["notes"]
            str_attr = chosen_character["data"]["str"]
            dex_attr = chosen_character["data"]["dex"]
            con_attr = chosen_character["data"]["con"]
            int_attr = chosen_character["data"]["int"]
            wis_attr = chosen_character["data"]["wis"]
            cha_attr = chosen_character["data"]["cha"]
            special_abilities = chosen_character["data"]["specialAbilities"]

            with main_cols[0]:
                writeCool(st, f"Strength: {str_attr}", 2)
                writeCool(st, f"Dexterity: {dex_attr}", 2)
                writeCool(st, f"Constitution: {con_attr}", 2)
                writeCool(st, f"Intelligence: {int_attr}", 2)
                writeCool(st, f"Wisdom: {wis_attr}", 2)
                writeCool(st, f"Charisma: {cha_attr}", 2)
                
                tripleCols = st.columns(4)
                writeCool(tripleCols[0], chosen_character["data"]["hp"], 3)
                writeCool(tripleCols[0], "Max HP", 1)
                writeCool(tripleCols[1], chosen_character["data"]["currentHP"], 3)
                writeCool(tripleCols[1], "Current HP", 1)
                writeCool(tripleCols[2], chosen_character["data"]["ac"], 3)
                writeCool(tripleCols[2], "AC", 1)
                writeCool(tripleCols[3], chosen_character["data"]["thac0"], 3)
                writeCool(tripleCols[3], "Thac0", 1)

            with name_column:
                writeCool(st, f"Name: {name}", 3)
            with level_column:
                writeCool(st, f"Level: {str(level)}", 2)
            with class_column:
                writeCool(st, f"Class: {occupation}", 2)
            with current_XP_column:
                writeCool(st, f"Current XP: {str(cxp)}", 2)
            with race_column:
                writeCool(st, f"Race: {race}", 2)
            with next_XP_column:
                writeCool(st, f"Next XP: {str(nxp)}", 2)
            with bonusXP_column:
                writeCool(st, f"XP Bonus: {str(bxp)}", 2)
            with notes_column:
                writeCool(st, f"Notes: {notes}", 2)
            #Character portrait MUST END IN .png, .jpg, or .jpeg. 
            with main_cols[1]:
                image_url = chosen_character["data"]["pictureURL"]
                st.image(image_url)
                # Special Abilities
                st.markdown("<h4 style='text-align: left; color: white;'>Special Abilities</h4>",
                        unsafe_allow_html=True)
                writeCool(st, special_abilities, 1)
        #Inventory Page
        elif st.session_state.PageNum == 2:
            with st.container():
                writeCool(st, "Welcome to your backpack, this includes all of your inventory!", 2)
                personalEquipmentTab, treasureTab, companionTab = st.tabs(
                    ["Personal equipment", "Treasure and magical items", "Companion/henchmen"])
            with personalEquipmentTab:
                writeCool(st, "Weight Allowance", 2)
                encumberanceCols = st.columns(5)
                writeCool(encumberanceCols[0], chosen_character["data"]["unencumbered"], 2)
                writeCool(encumberanceCols[0], "Unencumbered", 1)
                writeCool(encumberanceCols[1], chosen_character["data"]["light"], 2)
                writeCool(encumberanceCols[1], "Light", 1)
                writeCool(encumberanceCols[2], chosen_character["data"]["moderate"], 2)
                writeCool(encumberanceCols[2], "Moderate", 1)
                writeCool(encumberanceCols[3], chosen_character["data"]["heavy"], 2)
                writeCool(encumberanceCols[3], "Heavy", 1)
                writeCool(encumberanceCols[4], chosen_character["data"]["severe"], 2)
                writeCool(encumberanceCols[4], "Severe", 1)
                
                st.divider()
                inventoryCols = st.columns([.7,.3])
                writeCool(inventoryCols[0], "Inventory", 2)
                writeCool(inventoryCols[0], chosen_character["data"]["inventory"], 1)
                
                writeCool(inventoryCols[1], f'Weight: {chosen_character["data"]["weight"]}', 2)
                writeCool(inventoryCols[1], f'Food: {chosen_character["data"]["food"]}', 2)
                writeCool(inventoryCols[1], f'Water: {chosen_character["data"]["water"]}', 2)
                writeCool(inventoryCols[1], f'Ammo: {chosen_character["data"]["ammo"]}', 2)
                
            with treasureTab:
                writeCool(st, "Treasure, Magical Items, and Jewels", 2)
                writeCool(st, chosen_character["data"]["treasure"], 1)

            with companionTab:
                writeCool(st, "Henchmen and Animal Companions", 2)
                writeCool(st, chosen_character["data"]["companions"], 1)

        #Spells Page
        elif st.session_state.PageNum == 3:
            writeCool(st, "Spells", 2)
            writeCool(st, chosen_character["data"]["spells"])



        #Backstory
        elif st.session_state.PageNum == 4:
            writeCool(st, "Backstory", 2)
            columnbackstory = st.columns(3)
            writeCool(columnbackstory[1], chosen_character["data"]["backstory"], 2)

        
else:
    #Not logged in
    writeCool(st, "Please log in or register an account.", 2)
    
    if st.session_state.registering:
        # Currently registering
        with st.form("Please Register"):
            writeCool(st, "Username", 2)
            user = st.text_input("Username", label_visibility="collapsed")
            writeCool(st, "Password", 2)
            psword = st.text_input("Password", type= "password", label_visibility="collapsed")
            writeCool(st, "Confirm Password", 2)
            confirmpsword = st.text_input("Confirm Password", type= "password", label_visibility="collapsed")
            if st.form_submit_button("Register"):
                message, code = registerUser(user, psword, confirmpsword)
                st.write(message)
                if code:
                    st.session_state.PageNum = 0
                    st.experimental_rerun()
            
        st.button("Go to Log in", on_click=setRegistering, args=[False])
        
    else:
        # Currently not registering
        with st.form("Please Log in"):
            writeCool(st, "Username", 2)
            user = st.text_input("Username", label_visibility="collapsed")
            writeCool(st, "Password", 2)
            psword = st.text_input("Password", label_visibility="collapsed", type= "password")
            if st.form_submit_button("Log in"):
                message, code = UserLogin(user, psword)
                st.write(message)
                
                if code:
                    st.session_state.PageNum = 0
                    st.experimental_rerun()
    
        st.button("Go to Register", on_click=setRegistering, args=[True])

# Close the MongoDB connection
client.close()
