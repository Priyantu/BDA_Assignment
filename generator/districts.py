# 64 districts of Bangladesh. lat/lon and population are APPROXIMATE placeholders
# (rounded, from general knowledge). Replace with S1 (geoBoundaries centroids) and
# S2 (BBS Census 2022 / WorldPop) once downloaded. Population in millions.
D = {
"Dhaka": [("Dhaka",23.81,90.41,10.3),("Gazipur",24.00,90.42,4.0),("Narayanganj",23.62,90.50,3.1),("Narsingdi",23.92,90.72,2.4),
 ("Manikganj",23.86,90.00,1.6),("Munshiganj",23.55,90.53,1.5),("Tangail",24.25,89.92,4.0),("Kishoreganj",24.43,90.78,3.2),
 ("Faridpur",23.60,89.84,2.0),("Gopalganj",23.01,89.83,1.2),("Madaripur",23.17,90.20,1.2),("Rajbari",23.76,89.64,1.1),("Shariatpur",23.22,90.35,1.3)],
"Chattogram": [("Chattogram",22.34,91.83,9.2),("Cox's Bazar",21.45,91.98,2.8),("Cumilla",23.46,91.18,6.2),("Feni",23.02,91.40,1.6),
 ("Brahmanbaria",23.96,91.11,3.4),("Noakhali",22.82,91.10,3.6),("Lakshmipur",22.94,90.84,1.9),("Chandpur",23.23,90.67,2.7),
 ("Rangamati",22.65,92.18,0.65),("Khagrachhari",23.12,91.98,0.7),("Bandarban",22.20,92.22,0.48)],
"Rajshahi": [("Rajshahi",24.37,88.60,2.9),("Bogura",24.85,89.37,3.7),("Joypurhat",25.10,89.02,1.0),("Naogaon",24.80,88.94,2.9),
 ("Natore",24.41,89.00,1.8),("Chapainawabganj",24.60,88.28,1.8),("Pabna",24.00,89.23,2.9),("Sirajganj",24.45,89.70,3.4)],
"Khulna": [("Khulna",22.82,89.55,2.6),("Bagerhat",22.65,89.79,1.5),("Satkhira",22.71,89.07,2.1),("Jashore",23.17,89.21,3.1),
 ("Narail",23.17,89.50,0.8),("Magura",23.49,89.42,0.9),("Jhenaidah",23.54,89.17,2.0),("Kushtia",23.90,89.12,2.1),
 ("Chuadanga",23.64,88.85,1.2),("Meherpur",23.76,88.63,0.7)],
"Barishal": [("Barishal",22.70,90.37,2.4),("Bhola",22.69,90.65,1.8),("Patuakhali",22.36,90.33,1.7),("Pirojpur",22.58,89.97,1.2),
 ("Jhalokathi",22.64,90.20,0.7),("Barguna",22.15,90.12,1.0)],
"Sylhet": [("Sylhet",24.90,91.87,3.6),("Moulvibazar",24.48,91.77,2.1),("Habiganj",24.38,91.42,2.4),("Sunamganj",25.07,91.40,2.7)],
"Rangpur": [("Rangpur",25.75,89.25,3.1),("Dinajpur",25.63,88.64,3.3),("Kurigram",25.81,89.65,2.1),("Gaibandha",25.33,89.53,2.4),
 ("Nilphamari",25.93,88.86,2.0),("Lalmonirhat",25.99,89.45,1.4),("Thakurgaon",26.03,88.46,1.6),("Panchagarh",26.34,88.55,1.2)],
"Mymensingh": [("Mymensingh",24.75,90.40,5.1),("Jamalpur",24.92,89.94,2.4),("Netrokona",24.87,90.73,2.4),("Sherpur",25.02,90.02,1.5)],
}
ROWS = []
i = 1
for div, ds in D.items():
    for n, la, lo, p in ds:
        ROWS.append(dict(district_id=i, district=n, division=div, centroid_lat=la, centroid_lon=lo, population_est=int(p*1e6)))
        i += 1
assert len(ROWS) == 64
