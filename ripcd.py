#!/usr/bin/env python3.8

# Copyright (c) 2022, Adrian Moser
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# * Neither the name of the author nor the
# names of its contributors may be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile


def usage():
    sys.stderr.write('Usage: {} [-h] -d <directory> [-b <bitrate>]\n'.format(sys.argv[0]))
    sys.stderr.write('   -h display help\n')
    sys.stderr.write('   -b bitrate [32-320, default 192]\n')
    sys.stderr.write('   -d the target directory\n')
    sys.exit(1)


def get_track_file(path_prefix, track):
    return "%s/%02d %s.mp3" % (path_prefix, int(track['track']), sanitize(track['title']))


def sanitize(s):
    return s.replace("/", "-").replace(":", " -")


if __name__ == "__main__":
    target_dir = None
    bitrate = 192
    argc = 1

    while argc + 1 < len(sys.argv):
        if sys.argv[argc] == "-h":
            usage()
        elif sys.argv[argc] == "-d":
            target_dir = os.path.abspath(sys.argv[argc + 1])
            argc += 2
        elif sys.argv[argc] == "-b":
            bitrate = int(sys.argv[argc + 1])
            argc += 2
        else:
            break

    if target_dir is None or argc < len(sys.argv):
        usage()

    if not os.path.isdir(target_dir):
        sys.stderr.write("Directory '{}' doesn't exist\n".format(target_dir))
        exit(1)

    artist = None
    title = None
    year = None
    genre = None
    tracks = list()
    work_dir = tempfile.mkdtemp()

    os.chdir(work_dir)

    atexit.register(shutil.rmtree, work_dir)

    subprocess.check_call(["cdda2wav", "-alltracks", "-cddb", "1"])

    for file in os.listdir(work_dir):
        if file.endswith(".inf"):
            path = os.path.join(work_dir, file)

            with open(path, "r") as f:
                track = dict()

                track['file'] = path[:-3] + "wav"

                for line in f:
                    parts = re.split(r"\s*=\s*", line.rstrip(), 1)

                    if parts[0] == "Albumperformer" and artist is None:
                        artist = parts[1].rstrip("'").lstrip("'")
                    elif parts[0] == "Albumtitle" and title is None:
                        title = parts[1].rstrip("'").lstrip("'")
                    elif parts[0] == "Tracknumber":
                        track['track'] = parts[1]
                    elif parts[0] == "Tracktitle":
                        track['title'] = parts[1].rstrip("'").lstrip("'")

                tracks.append(track)

    cddb_file = os.path.join(work_dir, "audio.cddb")

    if os.path.exists(cddb_file):
        with open(cddb_file, "r") as f:
            for line in f:
                parts = re.split(r"\s*=\s*", line.rstrip(), 1)

                if parts[0] == "DYEAR":
                    year = parts[1]
                elif parts[0] == "DGENRE":
                    genre = parts[1]

    track_count = len(tracks)

    if track_count == 0:
        sys.stderr.write("No CDDB information available. Please process the files in {} manually\n".format(work_dir))
        atexit.unregister(shutil.rmtree)
        exit(1)

    path_prefix = os.path.join(target_dir, sanitize(artist), sanitize(title))

    os.makedirs(path_prefix, exist_ok=True)

    album_args = ["--ta", artist, "--tl", title, "--ty", year, "--tg", genre]

    for track in tracks:
        subprocess.check_call(["lame", "-b", str(bitrate), "-B", str(bitrate), "--tt", track['title'], "--tn",
                               "{}/{}".format(track['track'], track_count)] + album_args +
                              [track['file'], get_track_file(path_prefix, track)])
