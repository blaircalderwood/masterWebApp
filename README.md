# masterWebApp

The datasets for the project can be found here https://drive.google.com/drive/folders/0B2Xi66oU-r0KWG5JRmJGVkI2ZEk?usp=sharing 

These datasets do not contain the 39 co-occurrence matrix related databases due to their size. If a user wishes to create these the 'set_up' method must be called in the baseline comparison Python file.

The following is an overview of each created Python file:

Baseline Comparison - used to create training sets and run tests on the test set
Flickr Recommended - returns recommended tags for the Flickr Get Recommended baselines
Tag Co-occurrence - returns recommended tags for each other baseline and the novel system

Created files in the Context Retrieval folder:

Countries - contains methods used to extract country and continent information from images
Datetime Functions - extracts date or time related information from images
General Functions - contains an adaptation of binary search
Image Processing - extracts image content data
Location - contains all methods related to dynamic co-occurrence creation
Spreadsheet IO - saves data to spreadsheets
SQL extract - interfaces with the MySQL databases

Flickr API - Interfaces with the Flickr API
