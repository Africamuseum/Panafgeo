import pandas as pd
import pymysql
import yaml
import hashlib
import os
import warnings
from utils import fill_id_cols, relative_folder
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
EXCEL_PATH = os.getenv("EXCEL_PATH")

with open(DB_PATH, "r") as f:
    data = yaml.load(f, Loader=yaml.SafeLoader)
db = data["PMB_DB"]

def check_if_items_exist(series, col, table):
    sql = f"SELECT {col} FROM {table};"
    table_df = pd.read_sql(sql, con)
    table_df[col] = table_df[col].str.split("(").str[0].str.strip()
    not_known_series = series[~series.isin(table_df[col])]
    return not_known_series

def import_authors(authors_series):

    if len(authors_series) == 0:
        print("No authors to import...")
        return  pd.DataFrame()
    authors_df = pd.DataFrame(authors_series)
    authors_df["index_author"] = authors_df["author_name"].str.lower()
    # placeholders = ", ".join(["?"] * len(cols))
    sql = "INSERT INTO authors (author_type, author_name, index_author, author_import_denied) VALUES ('70', %s, %s, '1');"
    inserted_ids = []
    for row in authors_df.itertuples(index=False):
        cur.execute(sql, (row.author_name, row.index_author))
        inserted_ids.append(cur.lastrowid)
    authors_df["author_id"] = inserted_ids
    return authors_df

def insert_parents_nodes(categories_cols):
    categories_cols = list(check_if_items_exist(pd.Series(categories_cols), "libelle_categorie", "categories"))
    if len(categories_cols) == 0:
            print("Lucky, no parent category to insert...")
            return pd.DataFrame()
    select_sql = "SELECT MAX(id_noeud) FROM noeuds;"
    insert_sql = """
        INSERT INTO noeuds (num_parent, num_renvoi_voir, visible, num_thesaurus, path, authority_import_denied, not_use_in_indexation) 
        VALUES (1, 0, 1, 1, %s, 1, 0);
    """
    inserted_ids = []
    for col in categories_cols:
        cur.execute(select_sql)
        result = cur.fetchone()[0] + 1
        cur.execute(insert_sql, (result))
        inserted_ids.append(cur.lastrowid)
    parents_nodes_df = pd.DataFrame()
    parents_nodes_df["node_id"] = inserted_ids
    parents_nodes_df["category_value"] = categories_cols
    return parents_nodes_df

def get_parents_nodes(orphans_nodes_df):
    if len(orphans_nodes_df) == 0:
        print("Lucky, no orphan nodes to handle")
        return pd.DataFrame()
    sql = "SELECT num_noeud, libelle_categorie FROM categories WHERE libelle_categorie IN %s;"
    unique_category_type = tuple(orphans_nodes_df["category_type"].unique())
    cur.execute(sql, unique_category_type)
    result = cur.fetchone()
    reunited_nodes_df = pd.DataFrame({"node_id":result[0], "category_type":result[1]})
    return reunited_nodes_df

def insert_children_nodes(children_nodes_df, parents_nodes_df):
    children_nodes_df = children_nodes_df[children_nodes_df["category_value"].isin(check_if_items_exist(children_nodes_df["category_value"], "libelle_categorie", "categories"))]
    if len(children_nodes_df) == 0:
        print("Lucky, no children category to insert...")
        return pd.DataFrame()
    non_orphans_nodes_df = children_nodes_df.merge(parents_nodes_df.rename(columns={"node_id":"parent_node_id", "category_value":"category_type"}), on=["category_type"], how="inner")
    orphans_nodes_df = children_nodes_df[~children_nodes_df["category_value"].isin(non_orphans_nodes_df["category_value"])]
    reunited_nodes_df = get_parents_nodes(orphans_nodes_df)
    if len(reunited_nodes_df) != 0:
        non_orphans_nodes_df = pd.concat([non_orphans_nodes_df, orphans_nodes_df.merge(reunited_nodes_df, on=["category_type"], how="inner")])
    select_sql = "SELECT MAX(id_noeud) FROM noeuds;"
    insert_sql = """
        INSERT INTO noeuds (num_parent, num_renvoi_voir, visible, num_thesaurus, path, authority_import_denied, not_use_in_indexation) 
        VALUES (%s, 0, 1, 1, %s, 1, 0);
    """
    inserted_ids = []
    for row in non_orphans_nodes_df.itertuples(index=False):
        cur.execute(select_sql)
        result = cur.fetchone()[0] + 1
        cur.execute(insert_sql, (row.parent_node_id, f"{row.parent_node_id}/{result}"))
        inserted_ids.append(cur.lastrowid)
    non_orphans_nodes_df["node_id"] = inserted_ids
    return non_orphans_nodes_df

def import_nodes(categories_df):
    categories_df = categories_df[categories_df["category_value"].isin(check_if_items_exist(categories_df["category_value"], "libelle_categorie", "categories"))]
    if len(categories_df) == 0:
        print("Lucky, no category to insert...")
        return pd.DataFrame()
    select_sql = "SELECT MAX(id_noeud) FROM noeuds;"
    insert_sql = """
        INSERT INTO noeuds (num_parent, num_renvoi_voir, visible, num_thesaurus, path, authority_import_denied, not_use_in_indexation) 
        VALUES (1, 0, 1, %s, %s, 1, 0);
    """
    inserted_ids = []
    for row in categories_df.itertuples(index=False):
        cur.execute(select_sql)
        result = cur.fetchone()[0] + 1
        cur.execute(insert_sql, (row.num_thesaurus, result))
        inserted_ids.append(cur.lastrowid)
    categories_df["node_id"] = inserted_ids
    return categories_df

def import_categories(nodes_df):
    if len(nodes_df) != 0:
        nodes_df["index_categorie"] = nodes_df["category_value"].str.lower()
    sql = """
        INSERT INTO categories (num_thesaurus, num_noeud, langue, libelle_categorie, note_application, comment_public, comment_voir, index_categorie, 
        path_word_categ, index_path_word_categ) VALUES (1, %s, 'fr_FR', %s, '', '', '', %s, %s, %s);
    """
    for row in nodes_df.itertuples(index=False):
        cur.execute(sql, (row.node_id, row.category_value, row.index_categorie, row.category_value, row.index_categorie))

def import_authorities(nodes_series):
    sql = """
        INSERT INTO authorities (num_object, type_object, num_statut, thumbnail_url) VALUES (%s, 2, 1, ''); 
    """
    for index, value in nodes_series.items():
        cur.execute(sql, (value))

def import_notices(notices_df):
    notices_df["code"] = relative_folder(notices_df)
    notices_df["index_n_gen"] = notices_df["remarks"].str.lower()
    notices_df["index_n_resume"] = notices_df["content"].str.lower()
    notices_df["index_sew"] = notices_df["subfolder_title"].str.lower()
    sql = """
        INSERT INTO notices (typdoc, tit1, tit2, tit3, tit4, year, nocoll, code, npages, ill, size, accomp, n_gen, n_contenu, 
        n_resume, lien, index_l, index_serie, index_matieres, index_n_gen, index_n_contenu, index_n_resume, index_sew, index_wew, 
        commentaire_gestion, create_date, update_date, thumbnail_url) VALUES ('h', %s, %s, '', '', '', '', %s, '', '', '', '',
        %s, '', %s, '', '', '', '', %s, '', %s, %s, %s, '', NOW(), NOW(), '');
    """
    inserted_ids = []
    for i, row in enumerate(notices_df.itertuples(index=False)):
        if i % 50:
            print(i)
        if row.code.count("/") == 1:
            cur.execute(sql, (row.subfolder_title, row.sub_subfolder_title, row.code, row.remarks, row.content, row.index_n_gen, 
                              row.index_n_resume, row.index_sew, row.subfolder_title))
        elif row.code.count("/") == 2:
            cur.execute(sql, (row.sub_subfolder_title, row.subfolder_title, row.code, row.remarks, row.content, row.index_n_gen, 
                              row.index_n_resume, row.index_sew, row.subfolder_title))
        inserted_ids.append(cur.lastrowid)
    notices_df["notice_id"] = inserted_ids
    return notices_df[["code", "notice_id"]]

def link_authors_to_notices(notices_df, authors_df):
    tmp_df = notices_df
    tmp_df["author_name"] = [
        list(dict.fromkeys(n.strip() for n in names)) if isinstance(names, list) else names
        for names in tmp_df["author_name"].str.split(";")
    ]
    tmp_df["main_author"] = tmp_df["author_name"].str[0]
    tmp_df["secondary_authors"] = tmp_df["author_name"].str[1:]
    tmp_df = tmp_df.explode("author_name").dropna(subset=["author_name"]).reset_index(drop=True)
    tmp_df = tmp_df.merge(authors_df[["author_name", "author_id"]], on=["author_name"], how="inner")
    sql = """
        INSERT INTO responsability (responsability_author, responsability_notice, responsability_fonction, responsability_type, 
        responsability_ordre) VALUES (%s, %s, '070', %s, %s);
    """
    for row in tmp_df.itertuples(index=False):
        if row.author_name == row.main_author:
            responsability_type = 0
            responsability_ordre = 0
        elif row.author_name in row.secondary_authors:
            responsability_type = 1
            responsability_ordre = row.secondary_authors.index(row.author_name)
        cur.execute(sql, (row.author_id, row.notice_id, responsability_type, responsability_ordre))

def link_categories_to_notices(notices_df, categories_cols):
    categories_df = pd.DataFrame()
    for col in categories_cols:
        print(col)
        tmp_df = notices_df
        tmp_df[col] = [
            list(dict.fromkeys(n.strip() for n in names)) if isinstance(names, list) else names
            for names in tmp_df[col].str.split(";")
        ]
        tmp_df = tmp_df.explode(col).dropna(subset=[col]).reset_index(drop=True)
        nodes_df = pd.read_sql("SELECT id_noeud as node_id, libelle_categorie as category_value FROM categories INNER JOIN noeuds ON noeuds.id_noeud=categories.num_noeud;", con)
        nodes_df["category_value"] = nodes_df["category_value"].str.split("(").str[0].str.strip()
        tmp_df = tmp_df.merge(nodes_df[["node_id", "category_value"]], left_on=col, right_on=["category_value"], how="inner")
        categories_df = pd.concat([categories_df, tmp_df])
    sql = """
        INSERT INTO notices_categories (notcateg_notice, num_noeud, num_vedette, ordre_vedette, ordre_categorie)
        VALUES (%s, %s, 0, 1, 0); 
    """
    for row in categories_df.itertuples(index=False):
        cur.execute(sql, (row.notice_id, row.node_id))
    return categories_df

def insert_custom_values(notices_df, custom_cols):
    select_sql = "SELECT idchamp FROM notices_custom WHERE name = %s"
    for col in custom_cols:
        print(col)
        custom_values_df = notices_df[["notice_id"] + [col]]
        if col in ["square_degree", "company", "country", "old_province", "localities", "resource", "commodities"]:
            custom_values_df[col] = custom_values_df[col].str.split(";")
            custom_values_df = custom_values_df.explode(col)
        cur.execute(select_sql, (col,))
        result = cur.fetchone()
        for row in custom_values_df.itertuples(index=False):
            if col in ["commodities", "square_degree", "old_province", "localities", "resource", "country", "company"]:
                custom_field = "notices_custom_small_text"
            elif col in ["year_low", "year_high"]:
                custom_field = "notices_custom_integer"
            insert_sql = f"INSERT INTO notices_custom_values (notices_custom_champ, notices_custom_origine, {custom_field}, notices_custom_order) VALUES (%s, %s, %s, 0)"
            if pd.isna(row[1]) is False:
                cur.execute(insert_sql, (result[0], row[0], row[1]))

def compute_signature(notices_df, repertoire_id):
    cur.execute(f"SELECT repertoire_path FROM upload_repertoire WHERE repertoire_id = {repertoire_id}")
    result = cur.fetchone()[0]
    hash_list = []
    file_size_list = []
    for row in notices_df.itertuples(index=False):
            file_path = os.path.join(result, row.explnum_nomfichier)
            hash_processor = hashlib.sha256()
            try:
                with open(file_path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    file_size_list.append(f.tell())
                    f.seek(0)
                    for buf in iter(lambda: f.read(4096), b""):
                        hash_processor.update(buf)
                hash_list.append(hash_processor.hexdigest())
            except FileNotFoundError:
                file_size_list.append(0)
                hash_list.append("")
                if row.remarks.lower().contains("copie") or row.remarks.lower().contains("manquant"):
                    print(f"Error: specified file {file_path} not found but copy or missing folder")
                else:
                    print(f"Error: specified file {file_path} not found")
    return hash_list, file_size_list

def import_pdf_documents(notices_df, repertoire_id):
    sql = """
        INSERT INTO explnum (explnum_notice, explnum_bulletin, explnum_nom, explnum_mimetype, explnum_url, explnum_extfichier, explnum_nomfichier, explnum_statut, explnum_index_sew, 
        explnum_index_wew, explnum_repertoire, explnum_path, explnum_docnum_statut, explnum_signature, explnum_create_date, explnum_update_date, explnum_file_size) VALUES (%s, '0', %s, 'application/pdf',
        '', 'pdf', %s, '0', '', '', %s, '/', '1', %s, NOW(), NOW(), %s);
    """
    notices_df["explnum_nom"] = notices_df["code"].str.replace('/', '_')
    notices_df["explnum_repertoire"] = repertoire_id
    # notices_df["explnum_nomfichier"] = notices_df["explnum_nom"] + ".pdf"
    notices_df["explnum_nomfichier"] = "file-sample_150kB.pdf"
    hash_list, file_size_list = compute_signature(notices_df, repertoire_id)
    notices_df["explnum_signature"] = hash_list
    notices_df["explnum_file_size"] = file_size_list
    inserted_ids = []
    for row in notices_df.itertuples(index=False):
        if row.explnum_file_size != 0:
            cur.execute(sql, (row.notice_id, row.explnum_nom, row.explnum_nomfichier, row.explnum_repertoire, row.explnum_signature, row.explnum_file_size))
            inserted_ids.append(cur.lastrowid)
    return inserted_ids

repertoire_ids = [2]
ids_cols = ["folder_id", "subfolder_id", "subsubfolder_id"]
std_cols = ["subfolder_title", "sub_subfolder_title", "content", "remarks"]
categories_cols = ["document_type", "theme", "new_province"]
custom_cols = ["old_id", "square_degree", "company", "year_low", "year_high", "country", "old_province", "localities", "resource", "commodities"]
folder_ids = [5, 6, 7, 8, 11, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 254, 258, 259, 260, 262, 263, 268, 270, 272, 280]
# folder_ids = None

dict_cols = {"lieu_de_conservation":"conservation_place", "intitule_du_fond":"fund_title", "numero_dossier":"folder_id", 
                "numero_sous_dossier":"subfolder_id", "numero_sous_sous_dossier":"subsubfolder_id", "ancien_id":"old_id", "pays":"country", 
                "nouvelle_province":"new_province", "ancienne_province":"old_province", "degre_carre_concerne":"square_degree", 
                "localites":"localities", "entreprise":"company", "auteurs":"author_name", "annees":"years", "ressource":"resource", 
                "mineraux":"commodities", "titre_sous_dossier":"subfolder_title", "titre_sous_sous_dossier":"sub_subfolder_title", 
                "contenu":"content", "type_de_document":"document_type", "theme":"theme", "remarques":"remarks"}

with pymysql.connect(**db) as con:
    with con.cursor() as cur:
        try:

            excel_df = pd.read_excel(EXCEL_PATH)
            # excel_df = excel_df[:10]
            
            excel_df = excel_df.rename(columns=dict_cols)
            excel_df = excel_df[ids_cols + std_cols + categories_cols + custom_cols]
            
            print(excel_df.columns)

            if folder_ids:
                excel_df = excel_df[excel_df["numero_dossier"].isin(folder_ids)]

            excel_df = fill_id_cols(excel_df)

            print(len(excel_df))
            
            print("Number of rows before cleaning: ", len(excel_df))
            
            for col in ["country", "old_province", "new_province", "square_degree", "localities", "company", "author_name", "resource", "commodities", "document_type", "theme"]:
                excel_df[col] = excel_df[col].str.replace('\n', ';')
                excel_df[col] = excel_df[col].str.split(";").explode().str.strip().groupby(level=0).agg(list).str.join(";")
            
            for col in ["document_type", "theme", "new_province"]:
                excel_df[col] = excel_df[col].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.upper()
            excel_df["years"] = excel_df["years"].astype(str)
            excel_df["year_low"] = excel_df["years"].str.split('-').str[0]
            excel_df["year_high"] = excel_df["years"].str.split('-').str[1]
            excel_df = excel_df.drop("years", axis=1)
            for col in ["folder_id", "subfolder_id", "subsubfolder_id", "year_low", "year_high"]:
                excel_df[col] = excel_df[col].astype(str).str.replace('\xa0', '').str.replace('\u00a0', '').str.strip()
                excel_df[col] = pd.to_numeric(excel_df[col], errors='coerce')
                excel_df[col] = excel_df[col].astype("Int64")
            for col in ["old_id", "company", "author_name", "country", "new_province", "old_province", "square_degree", "localities", "resource", "commodities"]:
                excel_df[col] = excel_df[col].astype(str).str.replace('\xa0', '').str.replace('\u00a0', '').str.strip()
            for col in ["subfolder_title", "sub_subfolder_title", "content", "remarks"]:
                excel_df[col] = excel_df[col].fillna("")

            for col in excel_df.select_dtypes(include=[str]):
                excel_df[col] = excel_df[col].str.strip()

            print("Number of rows after cleaning:", len(excel_df))
            
            print(excel_df.dtypes)
            print(excel_df)
            
            authors_series = excel_df["author_name"].str.split(";").explode().drop_duplicates().dropna().reset_index(drop=True)
            authors_df = import_authors(authors_series)

            print("Number of authors inserted: ", len(authors_df))
            
            scientific_keywords_df = pd.DataFrame()
            scientific_keywords_df["category_value"] =  pd.Series(excel_df["theme"].str.split(";").explode().drop_duplicates().dropna().tolist() + excel_df["document_type"].str.split(";").explode().drop_duplicates().dropna().tolist())
            scientific_keywords_df["num_thesaurus"] = 1
            geographic_keywords_df = pd.DataFrame()
            geographic_keywords_df["category_value"] = pd.Series(excel_df["new_province"].str.split(";").explode().drop_duplicates().dropna().tolist())
            geographic_keywords_df["num_thesaurus"] = 2
            categories_df = pd.concat([scientific_keywords_df, geographic_keywords_df])
            nodes_df = import_nodes(categories_df)

            # Piece of code that could be useful if we want to add hierarchical structure for new category. Currently, existing categories are hierarchical and new one are inserted without any relations. The categories dict is formed as follow :
            # the key is/are the value of the parent.s category.ies and the value is the value of the child category
            # parents_nodes_df = insert_parents_nodes(tuple(categories_dict.keys()))
            # children_nodes_df = pd.DataFrame()
            # for key, value in categories_dict.items():
            #     child_node_df = pd.DataFrame()
            #     child_node_df["category_value"] = excel_df[value].str.split(";").explode().drop_duplicates().dropna().reset_index(drop=True)
            #     child_node_df["category_type"] = key
            #     children_nodes_df = pd.concat([children_nodes_df, child_node_df])
            # children_nodes_df = insert_children_nodes(children_nodes_df, parents_nodes_df)
            # if len(parents_nodes_df) != 0 or len(children_nodes_df) != 0:
            #     nodes_df = pd.concat([parents_nodes_df, children_nodes_df[["node_id", "category_value", "category_type"]]])
            
            import_categories(nodes_df)
            if len(nodes_df) != 0:
                import_authorities(nodes_df["node_id"])
            
            print("Number of categories inserted: ", len(categories_df))

            notices_df = import_notices(excel_df)
            print("Number of notices inserted: ", len(notices_df))
            
            link_authors_to_notices(excel_df, authors_df)

            categories_df = link_categories_to_notices(excel_df, categories_cols)

            insert_custom_values(excel_df, custom_cols)

            for repertoire_id in repertoire_ids:
                document_ids_list = import_pdf_documents(excel_df[["notice_id", "code", "remarks"]], repertoire_id)
            print("Number of documents imported: ", len(document_ids_list))
            con.commit()
        except FileNotFoundError as e:
            con.rollback()
            print("File not found: ", e)
        except Exception as e:
            con.rollback()
            print("Error: ", e)
