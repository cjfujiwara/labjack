
function out=TH_readLog(fname)
% Could use readtable, but it is slightly slower than text scan.
% Over many csv files with will add up (could consider going to SQL to
% further reduce time?)
    
    
    if exist(fname)
        disp(fname)
        fprintf('Reading file...')

        T1=now;
        fid=fopen(fname);
        hdr=textscan(fgetl(fid),'%s','delimiter',',');
        hdr=hdr{1};nhdr=length(hdr);
        fmt=['%q',repmat('%f',1,nhdr-1)];
        data=textscan(fid,fmt,'delimiter',',');
        fclose(fid);  
        T2=now;
        disp([' done (' num2str(round((T2-T1)*24*60*60,3)) ' s)']);
                
        T1=now;
        fprintf('Converting string to date...');
        data{:,1}=datetime(data{:,1},'InputFormat','MM/dd/yyyy, HH:mm:ss');    
        T2=now;
        disp([' done (' num2str(round((T2-T1)*24*60*60,3)) ' s)']);

        T1=now;
        fprintf('Making time table object');
        out=timetable(data{:,1},data{:,2:end},'VariableNames',hdr(2:end));
        T2=now;
        disp([' done (' num2str(round((T2-T1)*24*60*60,3)) ' s)']);
        disp(' ');
        
        
    else
        disp('no file');
        out=[];
    end
    
    
    % If you'd like to compare to readtable
%     tic
%     data2=readtable(fname);
%     data2.time=datetime(data2{:,1},'InputFormat','MM/dd/yyyy, HH:mm:ss');    
%     data2=table2timetable(data2);
%     out=data2;   
%     toc
end
