import os
from os.path import dirname, relpath, basename, getsize, join
import xxhash as xxh
import argparse
import pickle

parser = argparse.ArgumentParser(description="Small app to sync two remote filesystems with " +
                                             "shonky bandwidth that I visit frequently",
                                 prefix_chars="-\\")
parser.add_argument("-v", "--verbose", action="count", default=0)
parser.add_argument("-b", "--block-size", type=int, default=4096,
                    help="Override the default block size, specified in kBs")
group = parser.add_mutually_exclusive_group()
group.add_argument("-c", "--collision-check", action="store", metavar="Directory",
                   help="For debugging purposes. To see if the lazy fast-hash works appropriately")
group.add_argument("-p", "--parse", nargs=2,
                   metavar=("Input_Directory", "Output_Database"))
group.add_argument("-g", "--generate-actions", nargs=4,
                   metavar=("Database_1", "Database_2", "Transfer_directory", "Output_file"))

args = parser.parse_args()


def xxhash(filename, full_hash=False):
    chunk_size = args.block_size*1024
    hasher = xxh.xxh64()
    with open(filename, "rb") as file:
        if full_hash:
            buf = file.read()
        else:
            buf = file.read(chunk_size)
        hasher.update(buf)
    return hasher.hexdigest()


def collision_check(directory):
    print("Running on ",directory)
    bank = {}
    found = False
    for root, dirs, files in os.walk(directory):
        for file in files:
            h = xxhash(join(root, file))
            if h not in bank:
                bank[h]= join(root, file)
            else:
                f1 = bank[h]
                f2 = join(root, file)
                if xxhash(f1,True) == xxhash(f2,True):
                    if args.verbose >= 1:
                        print("Duplicate with hash " + h + " at " + f1 + " and " + f2)
                else:
                    if args.verbose >= 1:
                        print("Collision with hash " + h + " at " + f1 + " and " + f2)
                found = True
    return not found


class File(object):
    def __init__(self, full_path, root_dir=None, hash_function=None):
        if hash_function is None:
            self.hash_function = xxhash
        else:
            self.hash_function = hash_function
        self.file_name = basename(full_path)
        if root_dir is not None:
            self.path = relpath(dirname(full_path), root_dir)
            self.root_dir = root_dir
        else:
            self.path = dirname(full_path)
            self.root_dir = ""

        self.size = getsize(full_path)

        self.hash = self.hash_function(full_path)

    def rel_path(self):
        return join(self.path, self.file_name)

    def root_path(self):
        return join(self.root_dir, self.rel_path())


def parse(directory):
    path_dict = {}
    hash_dict = {}
    file_list = []

    for root, dirs, files in os.walk(directory):
        for file_name in files:
            if args.verbose:
                print(join(root, file_name))
            if getsize(join(root, file_name)) < 1024*4:
                continue
            f = File(join(root, file_name), directory)
            file_list.append(f)
            path_dict[f.rel_path()] = len(file_list)-1
            if f.hash in hash_dict:
                print(f.hash)
            hash_dict[f.hash] = len(file_list)-1

    return file_list, path_dict, hash_dict


def compare(a, b):
    file_list_A, path_dict_A, hash_dict_A = a
    file_list_B, path_dict_B, hash_dict_B = b

    checked = []
    dup = 0

    union = []
    Aonly = []
    Bonly = []

    location = []

    for hash in hash_dict_A:
        checked.append(hash)
        file_A = file_list_A[hash_dict_A[hash]]
        path_in_A = file_A.rel_path()
        if hash in hash_dict_B:
            file_B = file_list_B[hash_dict_B[hash]]
            path_in_B = file_B.rel_path()
            # Are these files in the same place?
            if path_in_A == path_in_B:
                # Yes! Hooray!
                union.append((hash, file_A))
            else:
                location.append((hash, file_A, file_B))
        else:
            Aonly.append((hash, file_A))

    for hash in hash_dict_B:
        if hash in checked:
            dup += 1
            continue
        checked.append(hash)
        file_B = file_list_B[hash_dict_B[hash]]
        path_in_B = file_B.rel_path()
        Bonly.append((hash, file_B))

    return union, Aonly, Bonly, location


def sizeof(FileList):
    cumulative = 0
    for file in FileList:
        cumulative += file[1].size
    return cumulative


def action_on(U, Ao, Bo, L, root_A, root_B):
    actions = []
    for hash, file in Ao:
        actions.append(["COPY RIGHT", join(root_A, file.rel_path()), join(root_B, file.rel_path())])
    for hash, file in Bo:
        actions.append(["COPY LEFT", join(root_B, file.rel_path()), join(root_A, file.rel_path())])
    for hash, fileA, fileB in L:
        pass
    return actions

if args.collision_check:
    print("Checking directory ", args.collision_check, " for collisions")
    c = collision_check(args.collision_check)
    if c:
        print("No collisions found")
    else:
        print("Collisions found")

if args.parse:
    input_dir, output_file = args.parse
    directory_structure = parse(input_dir)
    with open(output_file, 'w') as f:
        pickle.dump(directory_structure, open(output_file,"wb"))

if args.generate_actions:
    db1, db2, transfer_dir, output_file = args.generate_actions
    if not os.path.isdir(transfer_dir):
        print("Invalid directory ", transfer_dir)
    directory_structure1 = pickle.load(open(db1, "rb"))
    directory_structure2 = pickle.load(open(db2, "rb"))
    U, Ao, Bo, L = compare(directory_structure1, directory_structure2)
    print(action_on(U, Ao, Bo, L, root_directory_A, root_directory_B))
#
# collision_check(root_directory_A)
#
# A = parse(root_directory_A)
# B = parse(root_directory_B)
#
# U, Ao, Bo, L = compare(A, B)
#
# print(len(U), len(Ao), len(Bo), len(L))
# print(Ao)
# print(sizeof(Ao))
# print(Bo)
# print(sizeof(Bo))
# print(L)
# print(sizeof(L))
#
# print(action_on(U, Ao, Bo, L, root_directory_A, root_directory_B))
