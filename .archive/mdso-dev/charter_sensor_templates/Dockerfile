FROM artifactory.spectrumtoolbox.com/docker/blueplanet/bpo-onboard-helper:0.0.24

ADD . /

ENV SBIS=bpocore
ENV SBI_bpocore_southbound-update=update_etc_hosts_multi_provider

CMD ["bpo-onboard-helper", "--logfile=/bp2/log/bpo-onboard-helper.log", "--rpconfig=/rp_config.yaml"]
