FROM asciidoctor/docker-asciidoctor

RUN apk add --no-cache nodejs nodejs-npm ca-certificates openssl
RUN wget -qO- "https://github.com/dustinblackman/phantomized/releases/download/2.1.1/dockerized-phantomjs.tar.gz" | tar xz -C / && npm install -g phantomjs-prebuilt mermaid@7.0.9 --unsafe-perm
RUN echo '#!/bin/bash\nasciidoctor-pdf -r asciidoctor-diagram -a book-build -a allow-uri-read -a pdf-stylesdir=./resources -a pdf-style=./themes/bp-fsd-theme.yml -a pdf-fontsdir=resources/fonts index.adoc $@' > /usr/bin/publish && chmod +x /usr/bin/publish
