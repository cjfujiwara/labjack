function [hF, data] = labjack_cavity_plot(t1,t2,opts)

%% USER SETTINGS

if nargin == 0 
    t2 = now;           % T end
    t1 = now - 1;       % T start
    opts = struct;
    opts.dt = .2;        % Averaging time (minutes)
    opts.FigLabel = [];
    opts.doPlot = 1;
end

if ~isfield(opts,'dt')
    opts.dt = 0.2;
end

if ~isfield(opts,'FigLabel')
   opts.FigLabel = []; 
end

if ~isfield(opts,'doPlot')
    opts.doPlot = 1;
end


logRoot = 'Y:\LabJack\CavityLock\Logs';
hdrs = {'fsr meas (ms)', 'dt meas (ms)', 'dt set (ms)', 'vout (V)'};
%% Load the data

% Load the logs
tic
rawTbl=loadLogs(t1,t2);
te=toc;
disp(['Loading log files in ' num2str(round(te,3)) ' s']);

if isempty(rawTbl) || height(rawTbl)<5
   hF = [];
   data = [];
   return;
end

rawTbl.('df (GHz)') = (rawTbl.('dt meas (ms)')./rawTbl.('fsr meas (ms)'))*1.5;
if opts.dt>0
    % Resample the data using average to make plotting easier over long times
    tic
    pTable=retime(rawTbl,'regular','mean','timestep',minutes(opts.dt));
    te=toc;
    disp(['Averaged data in ' num2str(round(te,3)) ' s']);
else
   pTable=rawTbl; 
end

%% Process Data

% Grab data from data
dt      = pTable.('dt meas (ms)');
fsr     = pTable.('fsr meas (ms)');
v       = pTable.('vout (V)');
df      = pTable.('df (GHz)');
t       = pTable.Time;

% Restrict limits to the requested times
i=datenum(t)>datenum(t1);
t       = t(i);
df      = df(i);
v       = v(i);

data = timetable(t,df,v);
data.Properties.VariableNames = {'detuning (GHz)','voltage (V)'};

%% Plot

if opts.doPlot

    hF=figure;
    hF.Position=[50 100 800 300];
    set(hF,'color','w','NumberTitle','off');

    if exist('opts','var') && isfield(opts,'FigLabel') && ~isempty(opts.FigLabel)
       hF.Name = [opts.FigLabel ' Cavity Lock']; 
    else
        hF.Name = 'Cavity Lock';
    end

    % axes
    ax = axes;
    co=get(gca,'colororder');
    set(ax,'xgrid','on','ygrid','on','box','on','linewidth',1,'fontsize',10);
    datetick x
    xlabel('time');
    hold on

    yyaxis left
    pT=plot(t,df,'-','linewidth',1,'parent',ax,'color',co(1,:));
    ylabel('detuning (GHz)');

    yyaxis right
    pV=plot(t,v,'-','linewidth',1,'parent',ax,'color',co(2,:));
    ylabel('output (V)');

    lstr=['averaging : ' num2str(opts.dt) ' min'];
    text(5,5,lstr,'units','pixels','fontsize',14,'interpreter','none',...
        'verticalalignment','bottom','parent',ax);


    set(ax,'XLim',[datetime(datevec(t1)) datetime(datevec(t2))]);
else 
    hF = [];
end
%% Helper functions
    function T_all = loadLogs(t1,t2)
        t1=datenum(t1);
        t2=datenum(t2);
        
        clear T_all
        T_all = [];

        while floor(t1)<=floor(t2)
            mydatevec = datevec(t1);
            [fname,isFile] = getLogFile(logRoot,mydatevec);
            if isFile
%                 T = readtimetable(fname,'PreserveVariableNames',true);                
                T = readLog(fname);
                T_all = [T_all; T];
            end     
            t1=t1+1;          
        end 
    end
end


function [fileDay,fileexist] = getLogFile(logRoot,mydatevec)
if nargin == 1
    mydatevec = datevec(now);
end
dirYear  = [logRoot filesep num2str(mydatevec(1))];
dirMonth = [dirYear filesep num2str(mydatevec(1)) '.' sprintf('%2.2d',mydatevec(2))];
fileDay  = [dirMonth filesep sprintf('%2.2d',mydatevec(2)) '_' sprintf('%2.2d',mydatevec(3)) '.csv'];

if ~exist(logRoot,'dir')
   warning('No data server found.');
   fileDay = [];
   return;  
end

if ~exist(dirYear,'dir')
   mkdir(dirYear); 
end

if ~exist(dirMonth,'dir')
    mkdir(dirMonth);
end

fileexist=exist(fileDay,'file');
end


function out=readLog(fname)
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
        data{:,1}=datetime(data{:,1});    
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


