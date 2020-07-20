import argparse
import collections
import configparser
import hashlib
import os
import re
import sys
import zlib

# Definimos a los parser(os xD) para los argumentos de la línea de comandos
argparser = argparse.ArgumentParser(description="Content tracker")

argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
# Cada llamada a wyag *debe* tener un argumento (que lo leeremos con el subparser)
argsubparsers.required = True

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)

    if   args.command == "add"         : cmd_add(args)
    elif args.command == "cat-file"    : cmd_cat_file(args)
    elif args.command == "checkout"    : cmd_checkout(args)
    elif args.command == "commit"      : cmd_commit(args)
    elif args.command == "hash-object" : cmd_hash_object(args)
    elif args.command == "init"        : cmd_init(args)
    elif args.command == "log"         : cmd_log(args)
    elif args.command == "ls-tree"     : cmd_ls_tree(args)
    elif args.command == "merge"       : cmd_merge(args)
    elif args.command == "rebase"      : cmd_rebase(args)
    elif args.command == "rev-parse"   : cmd_rev_parse(args)
    elif args.command == "rm"          : cmd_rm(args)
    elif args.command == "show-ref"    : cmd_show_ref(args)
    elif args.command == "tag"         : cmd_tag(args)

class GitRepository(object):
    """Un repositorio de git."""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("%s no es un repositorio Git." % path)

        # Leemos el archivo de configuración .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
                self.conf.read([cf])
        elif not force:
            raise Exception("Archivo de configuración faltante.")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)

def repo_path(repo, *path):
    """Regresamos la dirección path dentro de el gitdir del repo."""
    return os.path.join(repo.gitdir, *path)

def repo_file(repo, *path, mkdir=False):
    """Computamos la dirección del archivo. Se crea dirname(*path) si no existe.
repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") creará
.git/refs/remotes/origin."""

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)

def repo_dir(repo, *path, mkdir=False):
    """Igual que repo_path pero mdkir *path si esta ausente y mkdir=True."""

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception("%s no es un directorio." % path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None

def repo_create(path):
    """Creamos un nuevo reposotirio en la dirección dada."""

    repo = GitRepository(path, True)

    # Nos aseguramos que path no exista o esté vacío.

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception ("%s no es un directorio." % path)
        if os.listdir(repo.worktree):
            raise Exception("%s no está vacío." % path)
    else:
        os.makedirs(repo.worktree)

    assert(repo_dir(repo, "branches", mkdir=True))
    assert(repo_dir(repo, "objects", mkdir=True))
    assert(repo_dir(repo, "refs", "tags", mkdir=True))
    assert(repo_dir(repo, "refs", "heads", mkdir=True))

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Repositorio sin nombre; edita este archivo para nombrar el repositorio.\n")

    # .git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo

def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret

argsp = argsubparsers.add_parser("init", help="Inicializa un nuevo y vacío repositorio.")

argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="Donde crear el repositorio.")

def cmd_init(args):
    repo_create(args.path)

def repo_find(path=".", required=True):
    """ Regresamos la primer carpeta que sea repositorio buscando recursivamente
    en el padre hasta llegar a /. """
    path = os.path.realpath(path)

    # ¡Lo encontramos!
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    # En otro caso buscamos en su padre...
    parent = os.path.realpath(os.path.join(path, ".."))

    # Caso base, cuando os.path.join("/", "..") == "/".
    if parent == path:
        if required:
            raise Exception("No se encontró ningún repositorio git.")
        else:
            return None

    # Hacemos recursión si aún no llegamos a la raiz
    return repo_find(parent, required)

