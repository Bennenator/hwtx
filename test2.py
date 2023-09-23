"""
Gamemaster's Mythical Mind
by Bennett Rodes, Tim Nyowheoma, and Oliver 

Usage: For hosting a local server, use streamlit run gmmm.py. Otherwise

"""



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
  background-image: url("https://img.freepik.com/free-photo/greet-final-battle-alone-illustration_456031-4.jpg");
  background-size: cover;
}
[data-testid="stHeader"] {
background-color: rgba(0, 0, 0, 0);
}
</style>
'''
#st.markdown(page_bg_img, unsafe_allow_html=True)

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
    font-weight: default;
    font-size: 24px;
    color: black;
    -webkit-text-stroke: 1px black;
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
if "ColumnNumber" not in st.session_state:
    st.session_state.ColumnNumber = 3

# This function takes in username and password strings, checks if they exist, and then authenticates the 
# input username and password
def UserLogin(username, password):
    if not username:
        return "Please enter a username", 0
    if not password:
        return "Please enter a password", 0
    
    uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)

    # Access the database and subcollections that handle storage of characters and logins
    db = client["GMMM"]
    login_info = db["users"]
    account = login_info.find_one({"username": username})
    if not account:
        return "Username not found", 0
    
    client.close()
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
    
    # Initialize the mongodb client
    uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)

    # Access the database and collection that handle storage of characters and logins
    db = client["GMMM"]
    login_info = db["users"]
    if login_info.count_documents({"username":username}) > 0:
        return "Username taken", 0
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    login_info.insert_one({"username": username, "password": hashed_password})
    st.session_state.registering = False
    st.session_state.loggedIn = True
    st.session_state.Username = username
    client.close()
    return "Registration successfull!", 1

# The following 4 helper functions are used in conjunction with buttons to serve as callback functions to update
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
        characters = list(queryMongo("characters", {"owner":st.session_state.Username}, findType = "All"))
        for character in characters:
            if character["data"]["name"] == name:
                return "Name taken", 0
        base_character = queryMongo("characters", {"owner":1}, findType = "One")
        base_character["data"]["name"] = name
        insertMongo("characters", [{"owner":st.session_state.Username, "data": base_character["data"]}])
        return "Character created!", 1

def updatePortion(characterID, changes):
    existing_character = queryMongo("characters", {"_id":characterID}, findType = "One")
    if existing_character:
        for key, value in changes.items():
            existing_character["data"][key] = value
        updateMongo("characters", ({"_id": characterID}, {"$set": {"data" : existing_character["data"]}}))
        return f"{existing_character['data']['name']} saved!"
    else:
        return "Character not found :("

# key_Updates must be tuple of form ({"_id": ID}, {"$set": object}) where ID is the matching "_id" field in the database and object is the new data of that object in the database
def updateMongo(databaseTitle, key_Updates_Tuple):
    # Initialize the mongodb client
    uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)

    # Access the database and  collections that handle storage of characters and logins
    db = client["GMMM"]
    sub_db = db[databaseTitle]
    output = sub_db.update_one(key_Updates_Tuple[0], key_Updates_Tuple[1])
    
    client.close()

# parameters a dictionary of the form that find_one() and find_all() use
def queryMongo(databaseTitle, parameters, findType="One"):
    uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"
    if findType == "One":
        # Initialize the mongodb client
        client = MongoClient(uri)

        # Access the database and subsub_dbs that handle storage of characters and logins
        db = client["GMMM"]
        sub_db = db[databaseTitle]
        output = copy.deepcopy(sub_db.find_one(parameters))
        client.close()
        return output
    else:
        # Initialize the mongodb client
        client = MongoClient(uri)

        # Access the database and subsub_dbs that handle storage of characters and logins
        db = client["GMMM"]
        sub_db = db[databaseTitle]
        output = copy.deepcopy(list(sub_db.find(parameters)))
        client.close()
        return output

# insertedItems must be iterable of items to insert
def insertMongo(databaseTitle, insertedItems):
    uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"
    # Initialize the mongodb client
    client = MongoClient(uri)

    # Access the database and  collection that handle storage of characters and logins
    db = client["GMMM"]
    sub_db = db[databaseTitle]
    for item in insertedItems:
        output = sub_db.insert_one(item)
    client.close()

# Changing between scenes in Gamemaster's Mythical Mind is handled by dynamic checking of session states,
# which are preserved through streamlit reruns (updates). The main logic of this large if-else statement is
# designed to display the page correctly after logging in or logging out.
if st.session_state.loggedIn == True:
    
    headbar = st.container()
    #characters is the list of character objects that have an "owner" attribute of the current logged in User.
    
    characters = queryMongo("characters", {"owner":st.session_state.Username}, findType = "All")
    chosen_character = characters[0] if characters else {"data":{}}
    
    character_header_dict = {character["data"]["name"]: character["data"]["pictureURL"] for character in characters}
     
    # This with structure is how streamlit likes to handle the sidebar object. In this case, the sidebar is 
    # designed to handle account management, character creation, and character selection.
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.Username}")
        st.button("Logout", on_click=logOut)
        
        # This with structure is how streamlit likes to handle form objects. Forms are neatly contained elements
        # ALWAYS with a single submit button and no other buttons.
        with st.form("Create a new character"):
            namefieldcol, namebcol = st.columns([7,3])
            namefield = namefieldcol.text_input("Enter new name", label_visibility = "collapsed", placeholder = "Enter a name")
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
    # Define the dictionary of categories and attribute names
    category_dict = {
        "Attributes": ["str", "dex", "con", "int", "wis", "cha"],
        "Character Info": ["name", "class", "race", "proficiencies", "level", "xpBonus", "pictureURL", "hp", "ac", "thac0", "backstory", "currentHP"],
        "Equipment": ["weapons", "inventory", "unencumbered", "light", "moderate", "heavy", "severe"],
        "Wealth": ["cp", "sp", "gp", "pp", "treasure"],
        "Resources": ["weight", "food", "water", "ammo", "companions", "spells"],
        "Special Abilities": ["specialAbilities", "notes"]
    }

    # Initialize the result dictionary
    result_dict = {}

    # Iterate through the category_dict
    for category, attributes in category_dict.items():
        category_subset = {}
        for attribute in attributes:
            if attribute in chosen_character["data"]:
                category_subset[attribute] = chosen_character["data"][attribute]
        if category_subset:
            result_dict[category] = category_subset
    
    # Define the number of columns for layout in st.session_state.ColumnNumber
    numColumns = 3

    # Initialize counters and containers
    counter = 0
    containerIndex = 0
    containers = [st.container()]  # Create a list of Streamlit containers
    containerColumns = []  # List to store columns within containers
    containerColumnExpanders = []  # List to store forms within columns

    # Loop through the items in result_dict
    for key, value in result_dict.items():
        # Create a new column within the current container
        containerColumns.append(containers[containerIndex].columns(numColumns))
        
        # Create an empty expander for each column
        containerColumnExpanders.append([{} for i in range(numColumns)])
        
        # Create an expander element for the current key in an expander element and store it in the expander dictionary
        containerColumnExpanders[containerIndex][counter][key] = containerColumns[containerIndex][counter].expander(f"{chosen_character['data']['name']}'s {key}:")
        
        # Iterate through the sub-items of the current key and add text input fields
        for subKey, subValue in value.items():
            containerColumnExpanders[containerIndex][counter][key].text_input(subKey, value=subValue, key=f"{subKey}")
        
        # Add a form submit button for saving the data
        if containerColumnExpanders[containerIndex][counter][key].button(f"Save {key}"):
            updatePortion(chosen_character["_id"], {megaSubKey:st.session_state[megaSubKey] for megaSubKey in value.keys()})
            st.experimental_rerun()
        # Check if the current counter reaches the specified number of columns
        if counter == numColumns - 1:
            # If so, move to the next container
            containerIndex += 1
            containers.append(st.container())  # Create a new container
            counter = 0
        else:
            # Otherwise, increment the counter for the current container
            counter += 1
    
    # Get the image URL from the chosen_character data
    image_url = chosen_character["data"]["pictureURL"]
    
    # Display the character's image in the first column of the first container
    # containerColumns[1][1].image(image_url)


    
    
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
