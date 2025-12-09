This is a README to document our apis. Yay!


#PORT
#### PUT
Parameters required are tid, port_id, and timer, as well as a JSON payload body containing {'activate': 'true' / 'false'}  
1. Create MDSO token
2. Call granite to get target (full fqdn) and vendor
3. Call MDSO passing the token, port_id, and target to see if a resource id exists
4. If no resource id exists, one must be created in MDSO using headers, tid, target, vendor, timer, 
port_id, product_id. 
    - If timer is set to zero, that leaves the port on.
    - If the timer is greater than 60, it's automatically set to 60.
5. After a resource is created, the API returns 'on-boarding'.
6. If an active resource id was found, MDSO is called to generate an operations id.
7. Finally, the MDSO token is deleted and the API returns the resource id and operations id on success. 


#### GET

#HEALTH
returns true if healthy

#NPA

