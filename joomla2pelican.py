"""Modules à importer"""
from lxml import etree
from os import path, makedirs, chdir, getcwd
import re

"""Variables globales"""
J2XML_FILE = "j2xml1590020161009001002.xml"
J2XML_POST_PATH = "/j2xml/content"
J2XML_CATEGORY_PATH = "/j2xml/category"
J2XML_IMAGE_PATH = "/j2xml/img"
READER = "markdown"

"""Fonction pour définir la catégorie du post dans Pelican :
Quatre valeurs possibles pour CATEGORY_LEVEL si l'article était dans une sous-catégorie
dans Joomla :
highest --> garder la catégorie de plus haut niveau
lowest --> garder la catégorie de plus bas niveau
concat --> garder tout et concaténer
hierarchy --> conserver la hiérarchie des catégories (nécessitera le plugin de Pelican
subcategory lors de la génération du site
Pour le moment, ne gère que deux niveaux de profondeur."""
CATEGORY_LEVEL = "hierarchy"

"""markup ou folder"""
CATEGORY_MODE = "markup"
OUTPUT_DIRECTORY = "content"

"""1) j2xml_introtext = garde le résumé tel qu'indiqué dans introtext, en
remplaçant les sauts de ligne par <br /> pour la compatibilité.
2) summary_max_length = fusionne introtext et fulltext pour utiliser le
paramètre summary_max_length
3) summary_plugin = fusionne introtext et fulltext en utilisant un séparateur.
Nécessite le plugin pour que la génération de Pelican fonctionne. """
SUMMARY_MODE = "summary_plugin"

"""Cette variable n'est utilisée que si SUMMARY_MODE est "summary_plugin" """
SUMMARY_PLUGIN_END = "<!-- PELICAN_END_SUMMARY -->"

"""Les articles de votre site contiennent-ils des images ? """
PROCESS_IMAGES = True

"""The part of each path will be ignored when using
IMAGES_HIERARCHY="keep_original" Optionnal. """
ORIGINAL_IMAGES_FOLDER = "/images/image_article"

"""The folder where you want to store your images. If not "images", don't forget
to add it to static paths in your Pelican configuration. """
IMAGES_FOLDER = "images"

"""The path to each image.
1. keep_original will preserve relative path from your Joomla website inside
   your newly defined IMAGES_FOLDER.
2. mirror_category will recreate a hierachy of folders mimicking the categories
   as defined by CATEGORY_LEVEL
3. None (default) will store all images inside IMAGES_FOLDER. Beware of
   duplicates."""
IMAGES_HIERARCHY = "keep_original"

#Utiliser attach ou filename pour les fichiers image liés ?
IMAGES_LINKS = "filename"

class Post:
    """Chaque post qui doit être construit dans le langage du reader
    (ici markdown ?) et qui est composé de différents éléments. """
    
    def __init__(self, post): # Notre méthode constructeur
        
        def call_xml(str):
            return post.xpath(str)[0].text
        
        def unescape2(str):
            from html import unescape
            if str is not None:
                str = unescape(str)
            else:
                str = ""
            return str
        
        def find_category(j2xml_catid):
            """Trouver le nom (titre) de la catégorie auquel correspond l'alias.
            Utilisé dans la fonction mkcat."""
            category = j2xml_catid
            for c in tree.xpath(J2XML_CATEGORY_PATH):
                cat2 = c[1].text
                if cat2 == category:
                    category = unescape2(c[3].text)
                    break
            return category
        
        def make_category():
            cat = post.xpath("catid")[0].text
            if CATEGORY_LEVEL is "highest":
                cat = cat.split("/")[0]
                cat = find_category(cat)
        #Please note we don't use split there because subcategoriies from
        #different categories can have the same name. Then, using the path is safer.
        #What's more, we don't know the depth of hierarchy.
            elif CATEGORY_LEVEL is "lowest":
                cat = find_category(cat)
            elif CATEGORY_LEVEL is "concat":
                subcat = find_category(cat)
                cat = find_category(cat.split("/")[0])
                cat = cat + " - " + subcat
            elif CATEGORY_LEVEL is "hierarchy":
                subcat = find_category(cat)
                cat = find_category(cat.split("/")[0])
                cat = cat + "/" + subcat
            else:
                cat = find_category(cat)
            return cat
        
        def pandoc(text):
            from subprocess import Popen, PIPE
            s = Popen(['pandoc', '-f', 'html', '-t', READER, "--wrap=none"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, errs = s.communicate(text.encode())
            output, errs = output.decode(), errs.decode()
            return output
        
        #Pour enlever les balises HTML restantes après le passage de Pandoc.
        def remove_html_tags(text):
            """Remove html tags from a string"""
            import re
            clean = re.compile('<.*?>')
            return re.sub(clean, '', text)
        
        def remove_duplicate_newlines(s):
            """ Remove duplicate newlines, leading blanks and backslashes 
            produced by Pandoc I don't know why. """
            import re
            s = re.sub(r'\n\s*\n', '\n\n', s)
            return s.replace("\\", "").lstrip()
        
        def make_summary():
            summary = remove_duplicate_newlines(remove_html_tags(pandoc(unescape2(call_xml("introtext")))))
            if SUMMARY_MODE is "j2xml_introtext":
                summary = "Summary: " + summary.replace("\n\n", "<br />")
                return summary
            elif SUMMARY_MODE is "summary_max_length":
                return summary
            elif SUMMARY_MODE is "summary_plugin":
                return summary + SUMMARY_PLUGIN_END
            else:
                return ""
                
            
        self.filename = call_xml("alias") + ".md"
        self.title = "Title: " + unescape2(call_xml("title"))
        self.date = "Date: " + call_xml("created")
        self.modified = "Modified: " + call_xml("modified")
        self.category = make_category()
        self.tags = "Tags: " + unescape2(call_xml("metakey"))
        self.slug = "Slug: " + call_xml("alias")
        self.author = "Author: " + unescape2(call_xml("created_by"))
        self.summary = make_summary()
        self.content = remove_duplicate_newlines(remove_html_tags(pandoc(unescape2(call_xml("fulltext")))))
        self.images = []

class Image:
    
    def __init__(self):
        self.filename = ""
        self.content = ""

def mkdir2(dir):
    """Redéfinit la fonction mkdir pour qu'elle ne s'exécute que si le dossier
    n'existe pas."""
    if not path.exists(dir):
        makedirs(dir)
        
def dir_and_file(filename):
    if not path.exists(path.dirname(filename)):
        try:
            makedirs(path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

def write_category(cat):
    """Fonction pour écrire la catégorie définie par mkcat, selon que l'on préfère 
    Utiliser la balise Category: ou une hiérarchie de dossiers."""
    if CATEGORY_MODE is "markup":
        cat = "Category: " + cat + "\n"
        return cat
    if CATEGORY_MODE is "folder":
        mkdir2(cat)
        chdir(cat)
        return ""
    
def format_images_urls(text):
    """Find images within the summary or the content, and save the image
    Filename or attach ?"""
    if IMAGES_HIERARCHY is "keep_original":
        #pattern = "(!\[.*\]\()" + ORIGINAL_IMAGES_FOLDER + "(.*)(/.*\.[a-zA-Z]{3}\))"
        pattern = ORIGINAL_IMAGES_FOLDER
        repl = "{" + IMAGES_LINKS + "}" + "/" + IMAGES_FOLDER
        return re.sub(pattern, repl, text)
    else:
        return ""

"""
# For both Python 2.7 and Python 3.x
import base64
with open("imageToSave.png", "wb") as fh:
    fh.write(base64.decodestring(imgData))
"""

def write_image(img):
    import base64
    """À retravailler pour éviter les redondances avec format_images_urls"""
    chdir(orig_path + "/" + OUTPUT_DIRECTORY)
    img_url = img.get("src")
    img_data = img.text.encode('utf-8')
    repl = IMAGES_FOLDER
    img_url = re.sub(ORIGINAL_IMAGES_FOLDER, repl, img_url)
    dir_and_file(img_url)
    with open(img_url, "wb") as fh:
        fh.write(base64.decodestring(img_data))
        fh.close()

orig_path = getcwd()

mkdir2(OUTPUT_DIRECTORY)

tree = etree.parse(J2XML_FILE)

for xml_post in tree.xpath(J2XML_POST_PATH):
    chdir(orig_path + "/" + OUTPUT_DIRECTORY)
    md_post = Post(xml_post)
    
    if PROCESS_IMAGES is True:
        md_post.summary = format_images_urls(md_post.summary)
        md_post.content = format_images_urls(md_post.content)
            
    md_post.category = write_category(md_post.category)
                  
    
    f = open(md_post.filename, 'w+')
    """for i in md_post:
        f.write(i)"""
    f.write(md_post.title + "\n" +
            md_post.date + "\n" +
            md_post.modified + "\n" +
            md_post.category +
            md_post.tags + "\n" +
            md_post.slug + "\n" +
            md_post.author + "\n" +
            md_post.summary + "\n" +
            md_post.content)
    f.close()

if PROCESS_IMAGES is True:
    for img in tree.xpath(J2XML_IMAGE_PATH):
        write_image(img)

""" TODO
1. Gérer les images. À part, seulement si IMAGES is True
2. Gérer les descriptions de catégories.
3. Proposer une option pour générer des tags ? Ou en faire un plugin pour
   Pelican ?
4. Gérer les profondeurs de catégorie supérieures à 2. """
