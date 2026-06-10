CREATE TABLE t0 (c0  PRIMARY KEY,       c4   );

CREATE TABLE t3 (c0   , c1 ,  BLOB, c3 ,  CLOB, c5 ,  TEXT,  NCHAR);
INSERT INTO t3 VALUES(72.519999999999996019,'2021-02-20',X'6b234f56614925413420',670412515,'lWYW?BoJXqa.PAxab','1zzJUdSU','ivPjAd','j-cQTi69rz.');
INSERT INTO t3 VALUES(92.760000000000005114,'2021-06-26',X'27',-967865178,'W 5rp','emKRmojiSl-SBt4Vcmcb','?z!gCb','bbFR5p7.aBZM7Z,0Aos');

CREATE TABLE t5 (c0   , c1 ,  CHARACTER);

INSERT INTO t5 VALUES('BNJaL01Lj3sMXZQT-A',2846408,'YEJ.ZsTrGheCmV');

INSERT INTO t5 VALUES('aZbvf3I7q,AKk',-1947983,'?l,nL9H');
INSERT INTO t5 VALUES('N1L0J1RZsIbuJ0!g',923750,'zo2oR');
INSERT INTO t5 VALUES('_JB5-Z!',-2877915,'dD0J0N-77?0Uo1e ,');
INSERT INTO t5 VALUES('Q_YOxU o',4636258,'Z_SRJld5gVFP');
INSERT INTO t5 VALUES('mNlEgKF2!',-584367,'wx_TvWXV');
INSERT INTO t5 VALUES('CuA1emC-R',1509128,'MDhbR RClrvKHOzN');
INSERT INTO t5 VALUES('mFCgpHaC-_',3353807,'usA8w_mSpY?_ TL');
INSERT INTO t5 VALUES('v,v77liG',4349642,'DXPmTZ.P2!Kx');
INSERT INTO t5 VALUES('crx8flX,g02DPmA',-1990450,'8GrbC9U_7Xhk');
INSERT INTO t5 VALUES('G-.Xe7',684380,'UrnRAA2g3VUV3 ');
INSERT INTO t5 VALUES('Q9AVRo28eIMSq',3937253,'9l4xWb.nvV?BgZ4c');
INSERT INTO t5 VALUES('9pYLxycVQp6B',2005450,',?!lycuysWJ');
INSERT INTO t5 VALUES('tHF9J0B9',-5586608,'z.jePZ7T-');
INSERT INTO t5 VALUES('FawzS_iRS82M',-5313409,'JqWLoScb');
INSERT INTO t5 VALUES('20EMpwWKwVfC8',7771574,'e65r1Y');
INSERT INTO t5 VALUES('Tz_CJnPo7,BwVipSd',2940263,'QtbpQ?E1w4Z.HCxWFM!');
INSERT INTO t5 VALUES('kya9nkIDJqikr9',6088621,'NuK?YToc7mCYQ6FBZo');
INSERT INTO t5 VALUES('j_jxija',-2685025,' QedKsQ_yLuMR.Y');
INSERT INTO t5 VALUES('05ytv3iYVR4iSWbaJ3da',-6561348,'sJG9T0M');
INSERT INTO t5 VALUES('z2p_pAo_DI8FfutF0',-1470225,'ZhJicQ');
INSERT INTO t5 VALUES('de GCJAmNWk1do7XAN?J',6645446,'Z_WaSBSPcXmzWvDYb!k');
INSERT INTO t5 VALUES('LSYOD5bxRq3.',2778922,'vbB6VDNCblDJ5D!fLvf');
INSERT INTO t5 VALUES('KUJR-z6b72tA,5j',3359107,'?1mic');
INSERT INTO t5 VALUES('bT-Nxqsh',-1028521,'g2SsLta,KC fnlM!EITo');
INSERT INTO t5 VALUES('?m9n_o',-5416584,'o2QDi5yH!b');
INSERT INTO t5 VALUES('Dr2T2W2',-8072188,'Vut!Zi4?');
INSERT INTO t5 VALUES('tfU3oMigZU1ZvvCdAmU6',5315105,'t-Vazhk');
INSERT INTO t5 VALUES('xXF-q2Re',-8369543,'fJ8_HW7Lf');
INSERT INTO t5 VALUES('tD5dr NbhE',83100,'2!mmVhgBRvs');
INSERT INTO t5 VALUES('5QC6bWkkO?i',1579836,'LH-Jz G');
INSERT INTO t5 VALUES('!A1rZ5g!-HGDXSvct',930168,'yIioLV');
INSERT INTO t5 VALUES('mKUBXhc6m3D- cn',-901863,'pnscE');
INSERT INTO t5 VALUES('Z43,OzKdAwr',8124048,'-p0kCOmOi4iLdqHsqKS');
INSERT INTO t5 VALUES('dthFdZTo',5302984,'M!x_f1QuMqSo');
INSERT INTO t5 VALUES('3E75kVioit ,',3912383,'UiE5FLuqN6');
INSERT INTO t5 VALUES('V?KxKy2FWQJ7deO!sb?f',5112056,'LRsV3glE4Y?');
INSERT INTO t5 VALUES('MV6H7EW,4-Q',500598,'iKbYn4mYe.mz6H!OfRi');
INSERT INTO t5 VALUES('wZfDq2b1t8',-5392615,'?XZp.GNkqxYR4');
INSERT INTO t5 VALUES('gcam8ECh9GLNzzO?',7774759,'MU3s2fK');

WITH 
            t1_stats AS (
                SELECT c1, 
                    COUNT()  count,
                    (c0)  avg_pk
                FROM t5
                GROUP BY c1
            ),
            t2_derived AS (
                SELECT c0, c3,
                    CASE 
                           
                        WHEN c3 < 50 THEN 'Low'
                         
                    END  category
                FROM t3
            )
            SELECT main.*, 
                (SELECT AVG(count) FROM t1_stats)  ,
                (
                    SELECT COUNT() FROM (
                        SELECT t3.c0, 
                                LAG(t3.c4) OVER()  ,
                                LEAD(t3.c4) OVER()  
                        FROM t0 t3
                        WHERE t3.c0 IN (
                            SELECT td.c0 FROM t2_derived td
                            
                            UNION
                            SELECT ts.avg_pk FROM t1_stats ts
                            WHERE ts.c1 = main.c1
                        )
                    ) 
                    
                )  
            FROM (
                SELECT ts.c1, td.category,
                    ts.count, ts.avg_pk,
                    DENSE_RANK() OVER( )  rank_in_category
                FROM t1_stats ts
                 JOIN (
                    SELECT  category FROM t2_derived
                ) td
            ) main
            
            ORDER BY main.category, main.rank_in_category;
