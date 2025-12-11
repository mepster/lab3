#/bin/sh

docker exec -it tljh-dev /bin/bash
docker exec --user jupyter-admin -it tljh-dev /bin/bash
docker exec --user jupyter-user1 -it tljh-dev /bin/bash


---


# make users on jh as admin
# login as each user to set pw

docker exec -it tljh-dev /bin/bash
[now on docker]
export JU=jupyter-user7
cd
cp .bashrc .profile /home/$JU
cp -rp /home/jupyter-admin/evosim /home/$JU 
chown -R $JU /home/$JU
chgrp -R $JU /home/$JU


---

Install conda in /usr/local/anaconda3.
conda create -n evosim python=3.9
conda activate evosim
conda install pandas scipy numpy tqdm svgwrite matplotlib termcolor
chgrp conda -R /usr/local/anaconda3/

# add evosim kernel to jupyter kernels
# manually log in to docker (with below) and run as each user:
conda run -n evosim python -m ipykernel install --user --name=evosim

git clone https://github.com/mepster/latticeproteins.git
pip install -e latticeproteins
cd latticeproteins
git checkout mep
cd ..

# login as root, or a user
JU=root ; WD=/root ; docker exec --user $JU -w $WD -it tljh-dev /bin/bash
JU=jupyter-admin ; WD=/home/$JU ; docker exec --user $JU -w $WD -it tljh-dev /bin/bash
JU=jupyter-user2 ; WD=/home/$JU ; docker exec --user $JU -w $WD -it tljh-dev /bin/bash


#export CMD="cat ../jupyter-admin/for-conda >> .bashrc "
#export CMD="git clone https://github.com/mepster/lab3.git"
for id in admin $(seq 1 5); do
    if [ "$id" = "admin" ]; then
        JU="jupyter-admin"
    else
        JU="jupyter-user${id}"
    fi
    echo "$JU"
    docker exec --user "$JU" -it -w "/home/$JU" tljh-dev /bin/bash -exec "$CMD"
done
# # set up user directories on tljh as root
# JU=root ; WD=/root ; docker exec --user $JU -w $WD -it tljh-dev /bin/bash
# # now on docker
# i=1; while [ "$i" -le 10 ]; do
#     export JU="jupyter-user${i}"
#     echo $JU
#     cp .bashrc .profile /home/$JU
#     cp -rp /home/jupyter-admin/evosim /home/$JU 
#     chown -R $JU /home/$JU
#     chgrp -R $JU /home/$JU
#     usermod -aG conda $JU
#     i=$((i+1))
#     done

# reset all users' WD repos
# on laptop
#export CMD="git clone https://github.com/mepster/lab3.git"
export CMD="git checkout -f ; git pull ; git checkout -f ; rm -f run.*"
export WD="lab3"
for id in admin $(seq 1 5); do
    if [ "$id" = "admin" ]; then
        JU="jupyter-admin"
    else
        JU="jupyter-user${id}"
    fi
    echo "$JU"
    docker exec --user "$JU" -it -w "/home/$JU/$WD" tljh-dev /bin/bash -exec "$CMD"
done

# run any CMD as each user
# on laptop
#export CMD="ls"
#export CMD="/opt/miniforge3/bin/conda env list"
export CMD="git checkout -f ; git pull ; git checkout -f ; rm -f run.*"
export WD="lab3"
for id in admin $(seq 1 5); do
    if [ "$id" = "admin" ]; then

        JU="jupyter-admin"
    else
        JU="jupyter-user${id}"
    fi
    echo "$JU"
    docker exec --user "$JU" -it -w "/home/$JU/$WU" tljh-dev /bin/bash -exec "$CMD"
done
