# Misc Py Image

The purpose of this image is to have a lighter weight alternative to the `build-image` which includes:

* various passwords
* scripts defined in `scripts/` dir

Anything that requires docker or special packages like mkpypi etc should use the `build-image` instead

Note:

* py3.7 only. (purposely left out pip2.7)