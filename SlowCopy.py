import os
from os.path import dirname, relpath, basename, getsize, join
import xxhash as xxh
import argparse

parser = argparse.ArgumentParser(description="")
group = parser.add_mutually_exclusive_group()
group.add_argument("-c","--collision-check")
group.add_argument("-p","--parse")
parser.add_argument("-d","--root-directory",action="store")


root_directory_A = "E:\\"
root_directory_B = "C:\\Users\\vossy\\Desktop\\E\\"


def fast_hash(filename):
    return getsize(filename)


def xxhash(filename):
    chunk_size = 4096*1024
    hasher = xxh.xxh64()
    with open(filename, "rb") as file:
        buf = file.read(chunk_size)
        hasher.update(buf)
    # file = open(filename,'rb')
    # H = xxh.xxh64(file.read())
    # file.close()
    return hasher.hexdigest()


def collision_check(directory):
    bank = []
    found = False
    for root, dirs, files in os.walk(directory):
        for file in files:
            H = fast_hash(join(root,file))
            if H not in bank:
                bank.append(H)
            else:
                print("Collision with hash ", H)
                found = True
    return found


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
            print(join(root,file_name))
            if getsize(join(root,file_name)) < 100:
                continue
            F = File(join(root, file_name), directory)
            file_list.append(F)
            path_dict[F.rel_path()] = len(file_list)-1
            if F.hash in hash_dict:
                print(F.hash)
            hash_dict[F.hash] = len(file_list)-1

    return file_list, path_dict, hash_dict


def compare(A,B):
    file_list_A, path_dict_A, hash_dict_A = A
    file_list_B, path_dict_B, hash_dict_B = B

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
            if path_in_A==path_in_B:
                # Yes! Hooray!
                union.append((hash, file_A))
            else:
                location.append((hash, file_A, file_B))
        else:
            Aonly.append((hash, file_A))

    for hash in hash_dict_B:
        if hash in checked:
            dup+=1
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
        actions.append(["COPY", join(root_A, file.rel_path()), join(root_B, file.rel_path())])
    for hash, file in Bo:
        actions.append(["COPY", join(root_B, file.rel_path()), join(root_A, file.rel_path())])
    for hash, fileA, fileB in L:
        pass
    return actions



#print(collision_check(root_directory_A))

A = parse(root_directory_A)
B = parse(root_directory_B)

U, Ao, Bo, L = compare(A,B)

print(len(U), len(Ao), len(Bo), len(L))
print(Ao)
print(sizeof(Ao))
print(Bo)
print(sizeof(Bo))
print(L)
print(sizeof(L))

print (action_on(U, Ao, Bo, L, root_directory_A, root_directory_B))