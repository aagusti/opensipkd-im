alter table smscmd  
    add field05 character varying(160),
    add field06 character varying(160),
    add field07 SmallInt,
    add field08 SmallInt;
    
alter table smsparsed  
    add field11 SmallInt;
    