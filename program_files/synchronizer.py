from multiprocessing import process
import os
import psutil
import re
import numpy as np
import subprocess
import music_tag
import socket
import paramiko
import json
import subprocess

gui_prompt = None   # function that asks for user input (set by app)
gui_wait_input = None  # function that blocks worker until input arrives

def ask_user(question, choices):
    if gui_prompt is None or gui_wait_input is None:
        raise RuntimeError("GUI callbacks not configured")
    
    gui_prompt(question, choices)  # tell GUI to show prompt
    return gui_wait_input()        # wait for GUI response
	
#	Procura uma external drive por name e devolve 'not' se não encontrar. Devolve a letra da drive se estiver montada
def find_external_drive(Drive):
	try:
		volume_info = os.popen("wmic logicaldisk get volumename,name").read()
		for line in volume_info.splitlines():
			splited_line = line.split(":")
			if len(splited_line) > 1:
				label = splited_line[1].strip()
				if label == Drive.label:
					letter = splited_line[0].strip()
					Drive.is_mounted = True
					Drive.path = letter + ":\\"
					break
	except Exception as e:
		print(f"An error occurred: {e}")



#	Upload para servidor via SSH
# def upload_to_server(hostname, port, username, password, local_file_path, remote_file_path):
#     # Initialize the SSH client
#     ssh = paramiko.SSHClient()
#     # Automatically add the server's host key (make sure to handle this securely in production)
#     ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     sftp = None  # Initialize sftp to None

#     try:
#         # Connect to the SSH server
#         ssh.connect(hostname, port, username, password)

#         # Initialize the SFTP client
#         sftp = ssh.open_sftp()

#         # Upload the file
#         sftp.put(local_file_path, remote_file_path)
#         print(f"File uploaded successfully to {remote_file_path}")

#     except Exception as e:
#         print(f"An error occurred: {e}")

#     finally:
#         # Close the SFTP session and SSH connection if they are open
#         if sftp:
#             sftp.close()
#         if ssh:
#             ssh.close()

def execute_rsync_on_remote(hostname, port, username, password, source_dir, destination_dir):
    # Initialize the SSH client
    ssh = paramiko.SSHClient()
    # Automatically add the server's host key (make sure to handle this securely in production)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the SSH server
        ssh.connect(hostname, port, username, password)

        # Properly quote the paths to handle special characters and spaces
        rsync_command = f"rsync -avz '{source_dir}' '{destination_dir}'"
        stdin, stdout, stderr = ssh.exec_command(rsync_command)

        # Read and print the output and error streams
        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            print("Output:\n", output)
        if error:
            print("Errors:\n", error)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the SSH connection if it is open
        if ssh:
            ssh.close()

def incremental_backup(hostname, port, username, password, local_source_dir, remote_destination_dir):
    # Initialize the SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the SSH server
        ssh.connect(hostname, port, username, password)

        # Walk through the local directory
        for root, dirs, files in os.walk(local_source_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, local_source_dir)
                remote_file_path = os.path.join(remote_destination_dir, relative_path)
                remote_file_path = remote_file_path.replace("\\", "/")  # Ensure forward slashes for remote paths

                # Get the last modified time of the local file
                local_mtime = os.path.getmtime(local_file_path)

                # Check if the remote file exists and get its last modified time
                sftp = ssh.open_sftp()
                try:
                    remote_file_attr = sftp.stat(remote_file_path)
                    remote_mtime = remote_file_attr.st_mtime
                except IOError:
                    remote_mtime = 0  # Assume the file doesn't exist or can't be accessed

                # Compare the last modified times and copy if the local file is newer
                if local_mtime > remote_mtime:
                    # Copy the file using scp
                    scp_command = f"scp {local_file_path} {username}@{hostname}:{remote_file_path}"
                    subprocess.run(scp_command, shell=True, check=True)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the SSH connection if it is open
        if ssh:
            ssh.close()

#######################################
#def folder_synch(origin,destination,operation):
	# command = "robocopy \"" + origin + " \" \""+ destination + " \" " + operation + " /r:3 /w:3"
	# os.system(command)
def folder_synch(origin, destination, operation):

    op_list = [opt for opt in operation.split(" ") if opt.strip()]

    command = ["robocopy", origin, destination] + op_list

    print("Running:", command)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
        shell=False
    )

    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(line, end="")  # goes straight to your Tk console

    process.wait()
########################################
def apply_tag(music_object, tag,value,filename):
	print("\n\t##### Aplicar \"" + tag + ":" + value + "\" a \"" + filename + "\" #####")
	music_object[tag] = value
	music_object.save()
########################################
def tag_song(full_song_path,artist_folder):
	#	Pegar no objecto e sacar titulo, artista e artista do album
	music_object = music_tag.load_file(full_song_path)
	titulo = str(music_object['tracktitle'])
	artista = str(music_object['artist'])
	artista_album = str(music_object['albumartist'])

	#	Pegar no filename do ficheiro
	music_full_path = str(os.path.splitext(full_song_path)[0])
	file_music_name = music_full_path.split(os.sep)[-1]

	if titulo != file_music_name:
		apply_tag(music_object,'tracktitle',file_music_name,file_music_name)
		
	if artista != artist_folder:
		apply_tag(music_object,'artist',artist_folder,file_music_name)

	if artista_album != artist_folder:
		apply_tag(music_object,'albumartist',artist_folder,file_music_name)
########################################
def tag_song_folder(music_folder, artist):
	#print("\n\t##### Tagging \"" + music_folder + "\" #####")
	for filename in os.listdir(music_folder):
		#	Ver full path de cada ficheiro dentro da pasta
		full_name = f"{music_folder}\{filename}"
		#	Se for uma pasta aplicar recursividade
		if os.path.isdir(full_name):
			tag_song_folder(full_name, artist)
		#	Se for ficheiro mp3 fazer tag
		elif os.path.splitext(filename)[1] == ".mp3":
			tag_song(full_name, artist)
########################################
def list_projects(folder,dict_main,dict_dup):
	#
	#	Procura na folder projetos e tenta adicionar a dict_main
	#	Se já houver um com o mesmo nome, mete em dict_dup 
	#
	#print("\n\t ##### Checking -> \"" + folder + "\"")
	for filename in os.listdir(folder):
		#print("\n\t\t ##### Found -> \"" + filename + "\" -> \"" + os.path.splitext(filename)[1] + "\"")
		full_name = f"{folder}\{filename}"
		#	Se for um diretório aplicar recursividade
		if os.path.isdir(full_name):
			list_projects(full_name,dict_main,dict_dup)
		else:
			#	Pegar na extensão do ficheiro
			#	Ver se é .als e ignorar caso esteja numa pasta de backup do ableton
			file_extension = os.path.splitext(filename)[1]
			if file_extension == ".als" and not folder.__contains__("Backup"):
				clean_project_name = filename
				if clean_project_name not in dict_main:
					#
					#	Acrescenta [nome do ficheiro .als] -> [pasta onde está o projeto]
					#
					#print("\n\t\t\tAppending {\"" + clean_project_name + "\" : \"" + folder + "}")
					dict_main[clean_project_name] = folder
				else:
					#
					#	Acrescenta [folder do projeto já existente] -> [folder do projeto duplicado]
					#
					#print("\n\t\t\t\tDuplicate of: \"" + clean_project_name + "\"")
					key = dict_main[clean_project_name]
					dict_dup[key] = folder
########################################
def delete_duplicates(list_of_duplicates):
	print("\n\tListing duplicates")
	if list_of_duplicates:
		for key in list_of_duplicates:
			print(f"\n\t\tGoing to synch:\n\t\t\t1. \"" + key + "\n\t\t\t2. \"" + list_of_duplicates[key])

		print("\n\t% Backup e apagar?\n\t%\t1. Sim\n\t%\t2. Não")
		#copy_option = input("\t% -> ")
		copy_option = ask_user("Backup e apagar?", [("Sim",1),("Não",2)])
		if copy_option != '2':
			for key in list_of_duplicates:
				if list_of_duplicates[key] in key and list_of_duplicates[key] != key:
					# =======================================================================================================
					#	Como o valor está contido na key significa que key é subpasta.
					#	Copiar tudo o que for mais recente da subpasta para a pasta principal e apagar a subpasta a seguir
					# =======================================================================================================
					folder_synch(key,list_of_duplicates[key]," /xo /s")
					command = "rmdir /s /q \"" + key + "\""
					os.system(command)
				else:
					delete_option = '0'
					while delete_option != '-1':
						print("\n\t\tGoing to synch:\n\t\t\t1. \"" + key + "\n\t\t\t2. \"" + list_of_duplicates[key] + "\n\t\t\t3. Nenhum" + "\n\t\tWhich one to DELETE?\n\t\t")
						delete_option = input("\n\t\t-> ")
						if delete_option == '1':
							folder_synch(key,list_of_duplicates[key]," /xo /s")
							command = "rmdir /s /q \"" + key + "\""
							os.system(command)
							delete_option = '-1'
						elif delete_option == '2':
							folder_synch(list_of_duplicates[key],key," /xo /s")
							command = "rmdir /s /q \"" + list_of_duplicates[key] + "\""
							os.system(command)
							delete_option = '-1'
						elif delete_option == '3':
							folder_synch(key,list_of_duplicates[key]," /xo /s")
							folder_synch(list_of_duplicates[key],key," /xo /s")
							delete_option = '-1'
						else:
							print("\n\t\tOpção não definida. Tenta outra vez!!!")
		else:
			print("\n\t\t##### Té já então #####")
	else:
		print("\n\t##### Não há duplicados :D")

# def delete_duplicates(list_of_duplicates):

#     print("\n\tListing duplicates")

#     if not list_of_duplicates:
#         print("\n\t##### Não há duplicados :D")
#         return

#     for key in list_of_duplicates:
#         print(f"\n\t\tGoing to synch:\n\t\t\t1. \"{key}\"\n\t\t\t2. \"{list_of_duplicates[key]}\"")

#     # Ask GUI whether to backup & delete
#     copy_option = get_gui_choice(
#         "Backup e apagar?",
#         [("1. Sim", "1"), ("2. Não", "2")]
#     )

#     if copy_option != "2":
#         for key in list_of_duplicates:

#             # Key is folder and value is its duplicate
#             if list_of_duplicates[key] in key and list_of_duplicates[key] != key:

#                 print("\n\tCopying more recent folder into main folder...")

#                 folder_synch(key, list_of_duplicates[key], "/xo /s")
#                 command = f'rmdir /s /q "{key}"'
#                 os.system(command)

#     else:
#         # Ask which folder to delete for each duplicate
#         for key in list_of_duplicates:

#             delete_option = get_gui_choice(
#                 f"Going to synch:\n1. \"{key}\"\n2. \"{list_of_duplicates[key]}\"\n3. Nenhum\nWhich one to delete?",
#                 [
#                     (f"1. {key}", "1"),
#                     (f"2. {list_of_duplicates[key]}", "2"),
#                     ("3. Nenhum", "3")
#                 ]
#             )

#             if delete_option == "1":
#                 folder_synch(key, list_of_duplicates[key], "/xo /s")
#                 os.system(f'rmdir /s /q "{key}"')

#             elif delete_option == "2":
#                 folder_synch(list_of_duplicates[key], key, "/xo /s")
#                 os.system(f'rmdir /s /q "{list_of_duplicates[key]}"')

#             else:
#                 print("\n\tNenhum selecionado. Mantendo ambos.")

#     print("\n\t##### Tê já então ####")

########################################
# def tag_synch_music(banda,option_list):
# 	src = local_full_repo + banda + "\\2. Músicas\\ "

# 	#	Tag das músicas no PC - retirar espaço no fim do path
# 	tag_song_folder(src.rstrip(), banda)

# 	for drive_index in option_list:
# 		dst = f"{list_of_drives[drive_index].path}" + "\\" + banda + "\\2. Músicas\\ "
# 		folder_synch(src, dst, " /xo /s")




# 	========================================================================
#	Ver quais são os projetos que já existem na origin e destination.
#	Fazer cópia incremental caso o projeto exista em ambos os lados
#	Copiar os que não existem em destination a partir da origin
#	========================================================================
def copy_band_projects(origin,destination,operation):
	#	========================================================================================
	#	Listar projetos na origem
	# 	Meter os resultado em list_of_local_projects e os duplicados em list_of_duplicates
	#	========================================================================================
	list_of_local_projects = {}
	list_of_duplicates = {}
	print(f"\n\t##### Listing {origin} ... ")
	list_projects(origin,list_of_local_projects,list_of_duplicates)
	
	#	Se existirem duplicados locais fazer deduplicação
	#if list_of_duplicates:
	#	delete_duplicates(list_of_duplicates)

	#	========================================================================================
	#	Listar projetos no destino 
	# 	Meter os resultado em list_of_remote_projects e os duplicados em list_of_duplicates
	#	Primeiro limpa list_of_duplicates
	#	========================================================================================
	print(f"\n\t##### Listing {destination} ... ")
	list_of_remote_projects = {}
	list_of_duplicates = {}
	list_projects(destination,list_of_remote_projects,list_of_duplicates)

	#	Se existirem duplicados locais fazer deduplicação
	#if list_of_duplicates:
	#	delete_duplicates(list_of_duplicates)
	print("\n\t##### Starting copy/synch ... ")

	#	========================================================================================
	#	Ver se para todos os .als locais existe um equivalente no destino
	#	Se não existir, copiar esse projeto para a pasta igual dentro da localização remota
	#	Caso já exista, fazer backup de um lado para o outro
	#	========================================================================================
	for project in list_of_local_projects:
		if project not in list_of_remote_projects:
			#	Pegar no indice de "origin" a partir do caminho do projeto
			#	Construir dst_path na destination desde posição indíce para a frente
			src_path = list_of_local_projects[project]
			origin_index = src_path.find(origin)
			path_after_origin = src_path[origin_index + len(origin):]
			dst_path = destination + "\\" + path_after_origin

			folder_synch(src_path,dst_path,operation)
		else:
	 		folder_synch(list_of_local_projects[project],list_of_remote_projects[project],operation)

