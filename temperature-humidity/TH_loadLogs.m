    function out=TH_loadLogs(t1,t2)
        t1=floor(datenum(t1));
        t2=floor(datenum(t2));
        out=TH_readLog(makeFileName(t1));
        while floor(t1)<=floor(t2)
            str=makeFileName(t1);
            if exist(str,'file')      
                thisdata=TH_readLog(str);
                if ~isempty(thisdata)
                    out=[out;thisdata];
                end
            end
            t1=t1+1;          
        end 
    end

    function str=makeFileName(t)
    % Root directory of logs
%     fldr='Y:\LabJack\Logging\Temperature-Humidity';
    fldr='X:\LabJackLogs\Temperature-Humidity';

    
       tV=datevec(t);       
       str=[fldr filesep num2str(tV(1)) filesep num2str(tV(1)) '.' ...
           num2str(tV(2),'%02.f') filesep num2str(tV(2),'%02.f') '_' datestr(t,'dd') '.csv'];
    end