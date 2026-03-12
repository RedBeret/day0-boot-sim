# Review Questions

1. Why does this repo model DHCP metadata instead of trying to run a raw DHCP service against the Windows host?
2. What is the difference between the current device record and the device timeline?
3. Why is `boot_file_uri` separate from the final bootstrap checksum?
4. What does the `RETRY_SCHEDULED` event teach that a plain failure would not?
5. Why is idempotency important for Day 0 workflows?
6. What evidence would you inspect first if the device never reached `READY`?
7. How does the synthetic PCAP complement the JSON timeline?
8. Why are the hostnames and IPs intentionally fake?
9. What changes if the optional TFTP service is enabled?
10. Where would you add another scenario if you wanted to simulate a different failure mode?
