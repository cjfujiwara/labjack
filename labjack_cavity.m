function labjack_cavity
%% Load Dependencies
disp(repmat('-',1,60));disp([mfilename '.m']);disp(repmat('-',1,60)); 

% Add all subdirectories for this m file
curpath = fileparts(mfilename('fullpath'));
addpath(curpath);addpath(genpath(curpath))  

%% GUI Settings
guiname = 'labjack_cavity';

% Find any instances of the GUI and bring it to focus, this is tof avoid
% restarting the GUI which may leave the shutter open.
h = findall(0,'tag','GUI');
for ii=1:length(h)
    
    if isequal(h(ii).Name,guiname)        
        warning(['Cavity GUI instance detected.  Bringing into focus. ' ...
            ' If you want to start a new instance, close the original cavity GUI.']); 
       figure(h(ii));
       return;
    end    
end

%% Default Settings
npt = struct;

% Labckjack default ip address
npt.myip='192.168.1.124';

% Digital trigger channel
npt.TRIGGER_NAME='DIO0'; % aka DIO0, must be DIO0 or DIO1 for triggered stream

% Analog input channels
npt.names = ['cavity','scan'];
npt.ScanListNames = {'AIN0','AIN1'} ;
npt.numAddresses = length(npt.ScanListNames);

% Analog output channels
npt.OUT = 'DAC0';
npt.outName = 'DAC0';

% Default acquisition speed
npt.scanRate = 20e3;
npt.numScans = 5000;
npt.delay = 0.2;

% Time Limits (ms)
npt.tLim = [100 240];
npt.dv = 1;

% Default lock mode
npt.LockMode=4;

% Acquisition is default off
npt.doAcq = 0;
%% Load LJM
% Make the LJM .NET assembly visible in MATLAB
ljmAsm = NET.addAssembly('LabJack.LJM');

% Creating an object to nested class LabJack.LJM.CONSTANTS
t = ljmAsm.AssemblyHandle.GetType('LabJack.LJM+CONSTANTS');
LJM_CONSTANTS = System.Activator.CreateInstance(t);
npt.handle = 0;

%% Figure and Panels

% Initialize the primary figure
hF=figure;
clf

set(hF,'Color','w','units','pixels','Name',guiname,...
    'toolbar','figure','Tag','GUI','CloseRequestFcn',@closeGUI,...
    'NumberTitle','off','Position',[50 50 600 500],...
    'SizeChangedFcn',@figResize);


% Callback for when the GUI is requested to be closed.
    function closeGUI(fig,~)
        disp('Closing labjack cavity GUI...');
        try  
            
            if npt.handle
               npt = disconnect(npt);
            end
        catch ME
            warning('Error when closing GUI.');
            warning(ME.message);
        end
        delete(fig);                % Delete the figure
    end

hpCon = uipanel('parent',hF,'units','pixels','backgroundcolor','w',...
    'title','connect');
hpCon.Position = [1 hF.Position(4)-75 200 75];

hpAcq = uipanel('parent',hF,'units','pixels','backgroundcolor','w',...
    'title','acquisition');
hpAcq.Position = [1 hF.Position(4)-195 200 120];

hpLock = uipanel('parent',hF,'units','pixels','backgroundcolor','w',...
    'title','lock');
hpLock.Position = [1 hF.Position(4)-335 200 140];

hpAx = uipanel('parent',hF,'units','pixels','backgroundcolor','w');
hpAx.Position = [hpCon.Position(3) 1 hF.Position(3)-hpCon.Position(3) hF.Position(4)];


%% Resize Callback
    function figResize(fig,~)
       if fig.Position(3) > 400 && fig.Position(4) > 400
        
           hpCon.Position(2) = hF.Position(4) - hpCon.Position(4);
           hpAcq.Position(2) = hpCon.Position(2) - hpAcq.Position(4);
           hpLock.Position(2) = hpAcq.Position(2) - hpLock.Position(4);
           
           hpAx.Position(3:4) = [hF.Position(3)-hpCon.Position(3) hF.Position(4)];       
       end
    end

%% Main plots

% ax = axes('parent',hpAx);
ax = subplot(3,1,[1 2],'Parent',hpAx);
set(ax,'box','on','linewidth',1,'xgrid','on','ygrid','on','fontsize',8);
xlabel('time (ms)');
ylabel('voltage (V)');
hold on

% Data plot
pData = plot(1,1,'k-');
yyaxis right

% Ramp Plot
sData = plot(1,1,'-');                  
% Low Time limit Plot
pLim1 = plot(npt.tLim(1)*[1 1],[0 10],'g--','linewidth',2);
% High Time limit plot
pLim2 = plot(npt.tLim(2)*[1 1],[0 10],'g--','linewidth',2);

% Peak A plot
pPeakA = plot(1,1,'rx','Visible','off');

% FSR A Plot
pFSRA = plot(1,1,'r-','Visible','off');
tFSRA = text(1,1,'a','units','data','verticalalignment','bottom',...
    'horizontalalignment','center','fontsize',8,'color','r',...
    'Visible','off');

% Peak B Plot
pPeakB = plot(1,1,'bx','Visible','off');

% FSR B Plot
pFSRB = plot(1,1,'b-','Visible','off');
tFSRB = text(1,1,'a','units','data','verticalalignment','bottom',...
    'horizontalalignment','center','fontsize',8,'color','b',...
    'Visible','off');

% Peak Delta Plot
pDelta = plot(1,1,'k-','Visible','off');

% Delta t text
tDelta = text(1,1,'a','units','data','verticalalignment','bottom',...
    'horizontalalignment','center','fontsize',8,'color','k',...
    'Visible','off');

% Output Voltage
tOutput= text(.01,.01,'OUTPUT','units','normalized','verticalalignment','bottom',...
    'horizontalalignment','left','fontsize',16,'color','k',...
    'Visible','on');

%
ax = subplot(3,1,3,'Parent',hpAx);
set(ax,'box','on','linewidth',1,'xgrid','on','ygrid','on','fontsize',8);
xlabel('time ago (s)');
xlim([0 60]);
hold on

%% Connection and Acquisition

% Connect
ttStr = 'Connect';
hb_connect=uicontrol(hpCon,'style','pushbutton','string','connect','Fontsize',10,...
    'Backgroundcolor','w','Callback',@doConnect,...
    'ToolTipString',ttStr,'backgroundcolor',[80 200 120]/255,'enable','on');
hb_connect.Position = [2 hpCon.Position(4)-40 70 20];

% Disconnect
ttStr = 'Disconnect';
hb_disconnect=uicontrol(hpCon,'style','pushbutton','string','disconnect','Fontsize',10,...
    'Backgroundcolor','w','Position',[81 1 80 20],'Callback',@doDisconnect,...
    'ToolTipString',ttStr,'backgroundcolor',[255 102 120]/255,...
    'enable','off');
hb_disconnect.Position =hb_connect.Position + [71 0 25 0];

% Ethernet IP address
tIP = uitable('parent',hpCon,'RowName',{'IP '},'ColumnName',{},...
    'fontsize',10,'data',{npt.myip},'ColumnWidth',{120},'ColumnEditable',true);
tIP.Position(3:4)=tIP.Extent(3:4);
tIP.Position(1:2) = [2 hb_connect.Position(2) - 30];

    function doConnect(~,~)
        disp('Connecting to labjack');
        npt=connect(npt);
        
        hb_connect.Enable='off';
        hb_disconnect.Enable='on';
        
        hb_startAcq.Enable='on';
        hb_stopAcq.Enable='off';
        hb_force.Enable='on';
    end

    function doDisconnect(~,~)
        disp('Disconnecting from labjack');
        npt=disconnect(npt);
        
        hb_connect.Enable='on';
        hb_disconnect.Enable='off';
        
        hb_startAcq.Enable='off';
        hb_stopAcq.Enable='off';
        hb_force.Enable='off';
    end

%% Acquisition

% start
ttStr = 'Force Acq';
hb_force=uicontrol(hpAcq,'style','pushbutton','string','force','Fontsize',10,...
    'Backgroundcolor',[255,255,255]/255,'Callback',@force,...
    'ToolTipString',ttStr,'enable','off');
hb_force.Position = [2 hpAcq.Position(4)-40 50 20];

% start
ttStr = 'Start Acq';
hb_startAcq=uicontrol(hpAcq,'style','pushbutton','string','start','Fontsize',10,...
    'Backgroundcolor','w','Callback',@startAcq,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[85 205 252]/255);
hb_startAcq.Position = hb_force.Position + [52 0 0 0];

% Stop
ttStr = 'Stop acquisition';
hb_stopAcq=uicontrol(hpAcq,'style','pushbutton','string','stop','Fontsize',10,...
    'Backgroundcolor','w','Position',[244 1 40 20],'Callback',@stopAcq,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[247, 168, 184]/255);
hb_stopAcq.Position = hb_startAcq.Position + [52 0 0 0];

% Acquisition Settings
n = {'Rate (Hz)', 'Num Scans','Delay (s)'};
tAcq = uitable('parent',hpAcq,'RowName',n,'ColumnName',{},...
    'fontsize',10,'data',[npt.scanRate; npt.numScans; npt.delay],...
    'ColumnWidth',{50},'ColumnEditable',true);
tAcq.Position(3:4)  =  tAcq.Extent(3:4);
tAcq.Position(1:2)  = [2 hb_stopAcq.Position(2) - 70];

    function force(~,~)
        disp([datestr(now,13) ' Forcing acquisition.']);
        npt=configureStream(npt);
        grabData
    end

    function startAcq(~,~)
        disp([datestr(now,13) ' Starting acquisition.']);
        npt.doAcq = 1;
        hb_startAcq.Enable='off';
        hb_stopAcq.Enable='on';
        hb_startLock.Enable='on';
        hb_stopLock.Enable='off';
        hb_force.Enable='off';
        npt.doLock = 0;        
        
        npt=configureStream(npt);
        configureDeviceForTriggeredStream(npt);
        configureLJMForTriggeredStream;
        drawnow;

        start(timer_labjack);    
    end

    function stopAcq(~,~)
        disp([datestr(now,13) ' Stopping acquisition.']);
        npt.doAcq = 0;
        hb_startAcq.Enable='on';
        hb_stopAcq.Enable='off';
        hb_startLock.Enable='off';
        hb_stopLock.Enable='off';
        npt.doLock = 0;
        hb_force.Enable='on';

        drawnow;                
        stop(timer_labjack);    
    end
%% Lock Graphics and Callbacks

% start
ttStr = 'Start lock';
hb_startLock=uicontrol(hpLock,'style','pushbutton','string','start lock','Fontsize',10,...
    'Backgroundcolor','w','Callback',@startLock,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[137 207 240]/255);
hb_startLock.Position = [2 hpLock.Position(4)-40 75 20];

% Stop
ttStr = 'Stop lock';
hb_stopLock=uicontrol(hpLock,'style','pushbutton','string','stop lock','Fontsize',10,...
    'Backgroundcolor','w','Position',[366 1 80 20],'Callback',@stopLock,...
    'ToolTipString',ttStr,'enable','off','backgroundcolor',[255,165,0]/255);
hb_stopLock.Position = hb_startLock.Position + [77 0 0 0];

% Lock Settings
n = {'T 1 (ms)', 'T 2 (ms)','T h (ms)','dV (mV)'};
tAcq = uitable('parent',hpLock,'RowName',n,'ColumnName',{},...
    'fontsize',10,'data',[npt.tLim(1); npt.tLim(2); npt.delay; npt.dv],...
    'ColumnWidth',{60},'ColumnEditable',true);
tAcq.Position(3:4)  =  tAcq.Extent(3:4);
tAcq.Position(1:2)  = [2 hb_stopLock.Position(2) - 90];

    function startLock(~,~)
        disp([datestr(now,13) ' Engaging lock.']);
        npt.doLock = 1;
        hb_startLock.Enable='off';
        hb_stopLock.Enable='on';  
        
        if npt.LockMode ==2        
            npt.FSR = range(pFSRA.XData);
            npt.Delta = range(pDelta.XData);
        end
        
        if npt.LockMode ==4
           npt.FSR = range(pFSRA.XData);
           npt.Delta = pFSRB.XData(1)-pFSRA.XData(1);
        end
        
        % Setup and call eReadName to read a value.
        [ljmError, value] = LabJack.LJM.eReadName(npt.handle, npt.OUT, 0);
        
        npt.OUT_VALUE_INIT = value;
        
        disp([' FSR   : ' num2str(npt.FSR)]);
        disp([' Delta : ' num2str(npt.Delta)]);
        disp([' Analog Output : ' num2str(npt.OUT_VALUE_INIT)]);        
    end

    function stopLock(~,~)
        disp([datestr(now,13) ' Stopping lock.']);
        npt.doLock = 0;
        hb_startLock.Enable='on';
        hb_stopLock.Enable='off';  
        
        npt.FSR = 0;
        npt.Delta = 0;
    end



%% Timr Objects

% Initialize the trig checker
timer_labjack=timer('name','Labjack Cavity Timer','Period',npt.delay,...
    'ExecutionMode','FixedSpacing','TimerFcn',@grabData);

    function grabData(~,~)
%         disp('grabbing data');
%         npt=configureStream(npt);
        configureDeviceForTriggeredStream(npt);
        configureLJMForTriggeredStream;
        pause(0.01);
        [yNew,isGood] = performStream;
        
        if isGood
            tNew = 1e3*(0:(size(yNew,2)-1))/npt.scanRate;

%             disp([datestr(now,13) ' New data.']);        
            updateData(tNew,yNew);
        else
           warning('error on data capture'); 
        end
    end

%% Data Stuff
    function updateData(t,y)        
        % Update data
        set(pData,'XData',t,'YData',y(1,:));
        set(sData,'XData',t,'YData',y(2,:));
        set(pLim1,'Ydata',[-5 50]);
        set(pLim2,'Ydata',[-5 50]);
    

        xlim([min(t) max(t)]);
        ylim([0 1.2]);

        % Find Peaks
        
        i1 = t > npt.tLim(1);
        i2 = t < npt.tLim(2);
        i = i1 & i2;
        
        [yPeak,Tp]=findpeaks(y(1,i),t(i),'MinPeakHeight',0.5,'MinPeakProminence',.4);        
        
        % Check current output voltage
        [ljmError, value] = LabJack.LJM.eReadName(npt.handle, npt.OUT, 0);
        npt.OUT_VALUE = value;        
        tOutput.String = ['$V_\mathrm{0} = ' num2str(value) '$ V'];
        tOutput.Interpreter='latex';
        
        if npt.LockMode == 2
            if length(yPeak)==2
                % All peaks are peak A
                TpA = Tp;
                yA = yPeak;        

                % Sort them by time
                [TpA,i]=sort(TpA);yA=yA(i);

                % Get the FSR
                FSR_A = range(TpA);

                % Find peak separatin
                Tdelta = TpA(1);

                % Update separation between peaks
                set(pDelta,'XData',[0 TpA(1)],...
                    'YData',[1 1]*yA(1),...
                    'Visible','on');
                set(tDelta,'String',[num2str(round(Tdelta,3)) ' ms'],...
                    'Visible','on');   
                tDelta.Position(1:2) = [mean(pDelta.XData) mean(pDelta.YData)];

                % Update peak identification data
                set(pPeakA,'XData',TpA,'YData',yA,'Visible','on'); 
                set(pPeakB,'Visible','off');            

                % Update FSR
                set(pFSRA,'XData',TpA,'YData',min(yA)*[1 1],'Visible','on')
                set(tFSRA,'String',[num2str(round(FSR_A,3)) ' ms'],...
                        'Visible','on');
                tFSRA.Position(1:2) = [mean(pFSRA.XData) mean(pFSRA.YData)];

                % Update FSR
                set(tFSRB,'Visible','off');

                if npt.doLock
                   v0 = npt.Delta; % Delta setpoint
                   v1 = Tdelta;    % Delta measure                 

                   % Only engage lock if FSR is correct
                   if abs(npt.FSR-FSR_A)/npt.FSR < 0.05
                      disp([v1 v0 FSR_A]);                

                       % Log Current Status
                       try
                            day_start=floor(now);
                            M = [(now-day_start)*24*60*60 npt.FSR v1 FSR_A v0 npt.OUT_VALUE];
                            fname='Y:\LabJack\CavityLock\Logs\2021\2021.10\11_05.csv';
                            dlmwrite(fname,M,'-append','delimiter',',');
                       catch ME
                           disp(fname)
                       end

                       % Increment by .5 mV if different (smallest step?)
                       newVal = value;
                       if v1>(v0+0.2)
                          newVal = value - 1e-3; 
                       end
                       
                       if v1<(v0-0.2)
                            newVal = value + 1e-3;
                       end


                        % Write the new value within capture range
                        if newVal~=value & abs(newVal-npt.OUT_VALUE_INIT)<.2
                            LabJack.LJM.eWriteName(npt.handle, npt.OUT, newVal);
                        end
                   end    
                end
            else
                pPeakA.Visible='off';
                pPeakB.Visible='off';
                pDelta.Visible='off';
                tDelta.Visible='off';
                pFSRA.Visible='off';
                tFSRA.Visible='off';
            end
        end     
        
        if npt.LockMode ==4
            if length(yPeak)==4               

                % sort in descending order of height
                [yPeak,inds]=sort(yPeak,'descend');
                Tp=Tp(inds);                
                
                % Two tallet peaks are peak A
                TpA = Tp(1:2);
                yA = yPeak(1:2);
                
                % Next two tallest peaks are peak B
                TpB = Tp(3:4);
                yB = yPeak(3:4);

                % Sort them by time
                [TpA,ia]=sort(TpA);yA=yA(ia);
                [TpB,ib]=sort(TpB);yB=yB(ib);

                % Get the FSR
                FSR_A = range(TpA);
                FSR_B = range(TpB);

                % Find peak separatin
                Tdelta = TpB(1)-TpA(1);            

                % Update separation between peaks
                set(pDelta,'XData',[TpA(1) TpB(1)],...
                    'YData',[1 1]*mean([yA(1) yB(1)]),...
                    'Visible','on');
                set(tDelta,'String',[num2str(round(abs(Tdelta),3)) ' ms'],...
                    'Visible','on');   
                tDelta.Position(1:2) = [mean(pDelta.XData) mean(pDelta.YData)];

                % Update peak identification data
                set(pPeakA,'XData',TpA,'YData',yA,'Visible','on');
                set(pPeakB,'XData',TpB,'YData',yB,'Visible','on');

                % Update FSR A
                set(pFSRA,'XData',TpA,'YData',min(yA)*[1 1],'Visible','on')

                set(tFSRA,'String',[num2str(round(FSR_A,3)) ' ms'],...
                        'Visible','on');
                tFSRA.Position(1:2) = [mean(pFSRA.XData) mean(pFSRA.YData)];

                % Update FSR B
                set(pFSRB,'XData',TpB,'YData',min(yB)*[1 1],'Visible','on')

                set(tFSRB,'String',[num2str(round(FSR_B,3)) ' ms'],...
                        'Visible','on');
                tFSRB.Position(1:2) = [mean(pFSRB.XData) mean(pFSRB.YData)];

                if npt.doLock
                   v0 = npt.Delta; % Delta setpoint
                   v1 = Tdelta;    % Delta measure                 

                   % Only engage lock if FSR is correct
                   if abs(npt.FSR-FSR_A)/npt.FSR < 0.05
                      disp([v1 v0 FSR_A]);                

                       % Log Current Status
                       try
                            day_start=floor(now);
                            M = [(now-day_start)*24*60*60 npt.FSR v1 FSR_A v0 npt.OUT_VALUE];
                            fname='Y:\LabJack\CavityLock\Logs\2021\2021.10\11_05.csv';
                            dlmwrite(fname,M,'-append','delimiter',',');
                       catch ME
                           warning('unable to log data');
                       end                        
                       
                       newVal = value;  % New voltage is the old one
                       doWrite = 0;     % Don't write a new voltage by default
                       
                       % Is the value sufficiently above the set point?
                       if v1>(v0+0.2)
                          % Increment by 1mV and enable writing
                          newVal = value - 1e-3; 
                          doWrite = 1;
                       end
                       
                      % Is the value sufficiently below the set point?
                       if v1<(v0-0.2)
                           % Increment by 1mV and enable writing
                            newVal = value + 1e-3;
                            doWrite = 1;
                       end
                       
                       % Write the new voltage if necessary
                       if doWrite
                           % Check if new voltage is within capture range
                           if abs(newVal - npt.OUT_VALUE_INIT)<0.2
                               LabJack.LJM.eWriteName(npt.handle, ...
                                   npt.OUT, newVal);
                               disp('writing');
                           else
                               warning('Unable to write value outside of voltage limits');
                           end                           
                       end
                   end    
                end  
            else
                pPeakA.Visible='off';
                pPeakB.Visible='off';
                pDelta.Visible='off';
                tDelta.Visible='off';
                pFSRA.Visible='off';
                tFSRA.Visible='off';
                pFSRB.Visible='off';
                tFSRB.Visible='off';
            end
        end
        
        drawnow;
    end


%% Labjack Functions


function [Y_ALL,isGood] = performStream

    % Initializing Bookkeeeping variables
    totScans = 0;
    totSkip = 0;
    i = 0;
    dataAll = {};
    isGood = 1;
    LJMScanBacklog=0;
    
    tstart=now;
    
    noScanNum = 0;
    noScanMax = 5;
    
    fprintf([datestr(now,13 ) ' Streaming ...']);
    
    % Begin the Stream
    [~, npt.scanRate] = LabJack.LJM.eStreamStart(npt.handle, npt.scansPerRead, ...
        npt.numAddresses, npt.aScanList, npt.scanRate);

    while (totScans<npt.numScans) && isGood       
        
        sleepTime = double(npt.scansPerRead)/double(npt.scanRate);

        pause(sleepTime);
        
        try
            % Read data in buffer
            [~, devScanBL, ljmScanBL] = LabJack.LJM.eStreamRead( ...
                npt.handle, npt.aData, 0, 0);

            % Update scans
            totScans = totScans+npt.scansPerRead;

            % Update skipped measurements
            curSkip = sum(double(npt.aData)==-9999.0);
            totSkip = totSkip + curSkip;
            % Increment stream read
            i = i+1;        

            % Append Data
            dataAll{i}=npt.aData;     
        catch ME
            
            if isequal(char(ME.ExceptionObject.LJMError) ,'NO_SCANS_RETURNED')
%                 disp([datestr(now,13) ' no scans']);  
                noScanNum = noScanNum + 1;
                if noScanNum >= noScanMax
                    npt=disconnect(npt);
                    npt=connect(npt);
                    npt=configureStream(npt);
                    isGood = 0;
                end
            else
                isGood=0;
            end

        end          
    end
    try
        LabJack.LJM.eStreamStop(npt.handle);
    end
    Y_ALL=[];
    for kk=1:length(dataAll)
        Y = double(dataAll{kk});
        Y = reshape(Y,[npt.numAddresses length(Y)/npt.numAddresses]);
        Y_ALL = [Y_ALL Y];
    end  
    tend=now;
    
    disp([' done (' num2str(round((tend-tstart)*24*60*60,2)) 's)']);
end


function npt = connect(npt)
    try
        % Ethernet Connect
        fprintf('Connecting to labjack ... ');
        [ljmError, npt.handle] = LabJack.LJM.OpenS('T7', 'ETHERNET', npt.myip, npt.handle);
        
% USB
%         [ljmError, npt.handle] = LabJack.LJM.OpenS('T7', 'USB', 'ANY', npt.handle);

        
        disp( ' done');

        try
            [ljmError] = LabJack.LJM.eStreamStop(npt.handle);
        end
        showDeviceInfo(npt.handle);    
       
    end
end

function npt=disconnect(npt)
    disp('Disconnecting');
    LabJack.LJM.Close(npt.handle);
    npt.handle=0;
end

    function configureLJMForTriggeredStream
        LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_SCANS_RETURN,...
            LJM_CONSTANTS.STREAM_SCANS_RETURN_ALL_OR_NONE);
%         LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_SCANS_RETURN,...
%             1);
        
%         LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_RECEIVE_TIMEOUT_MS,...
%             0);  
        LabJack.LJM.WriteLibraryConfigS(LJM_CONSTANTS.STREAM_RECEIVE_TIMEOUT_MS,...
           30);  
    end

function configureDeviceForTriggeredStream(npt)
%     """Configure the device to wait for a trigger before beginning stream.
% 
%     @para handle: The device handle
%     @type handle: int
%     @para triggerName: The name of the channel that will trigger stream to start
%     @type triggerName: str
%     """

    LabJack.LJM.eWriteName(npt.handle, 'STREAM_TRIGGER_INDEX', 2000);

    % Clear any previous settings on triggerName's Extended Feature registers    
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_ENABLE'], 0);
%https://labjack.com/support/datasheets/t-series/digital-io/extended-features/pulse-width
    % EF_IDEX --> 5 pulse width in
    % EF_CONFIG_A is continues or one shot (??)
    
    % 5 enables a rising or falling edge to trigger stream
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 5);
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 12);

% This works
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 5);
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_CONFIG_A'], 0);

% This works
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 3);    
%     LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_CONFIG_A'], 1);


% This works?
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_INDEX'], 4);    
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_CONFIG_A'], 1);
    
    % Enable
    LabJack.LJM.eWriteName(npt.handle, [npt.TRIGGER_NAME '_EF_ENABLE'], 1);

end


function npt = configureStream(npt)
    T = npt.numScans * npt.numAddresses /npt.scanRate;

    disp(['nScan=' num2str(npt.numScans) ',' ...
        'nAddr=' num2str(npt.numAddresses) ',' ...
        'rScan=' num2str(npt.scanRate) ' Hz' ...
        ' ==> ' num2str(round(T,1)) ' seconds']);
    t1 = now;
    fprintf('Configuring data stream ...');

    % Scan list names to stream.
    aScanListNames = NET.createArray('System.String', npt.numAddresses);    
    for kk=1:npt.numAddresses
        aScanListNames(kk) = npt.ScanListNames{kk};
    end
    npt.aScanListNames = aScanListNames;

    % Create Scan List
    npt.aScanList = NET.createArray('System.Int32', npt.numAddresses);
    % Dummy array for aTypes parameter
    npt.aTypes = NET.createArray('System.Int32', npt.numAddresses);
    LabJack.LJM.NamesToAddresses(npt.numAddresses, npt.aScanListNames, ...
        npt.aScanList, npt.aTypes);

    % Setup the scan Rate and ata
%     npt.scansPerRead = min([int32(npt.scanRate/2) int32(npt.numScans)]);
    npt.scansPerRead = npt.numScans;
    % Stream reads will be stored in aData. Needs to be at least
    % numAddresses*scansPerRead in size.
    npt.aData = NET.createArray('System.Double', npt.numAddresses*npt.scansPerRead);

    LabJack.LJM.eWriteName(npt.handle, 'STREAM_TRIGGER_INDEX', 0); % Trigger
    LabJack.LJM.eWriteName(npt.handle, 'STREAM_CLOCK_SOURCE', 0);  % Timing

    % All negative channels are single-ended, AIN0 and AIN1 ranges are
    % +/-10 V, stream settling is 0 (default) and stream resolution index
    % is 0 (default).
    numFrames = 4;
    aNames = NET.createArray('System.String', numFrames);
    aNames(1) = 'AIN_ALL_NEGATIVE_CH';
    aNames(2) = 'AIN0_RANGE';
    aNames(3) = 'STREAM_SETTLING_US';
    aNames(4) = 'STREAM_RESOLUTION_INDEX';
    aValues = NET.createArray('System.Double', numFrames);
    aValues(1) = LJM_CONSTANTS.GND;
    aValues(2) = 10.0;
    aValues(3) = 0;
    aValues(4) = 0;

    % Write the analog inputs' negative channels (when applicable), ranges
    % stream settling time and stream resolution configuration.
    LabJack.LJM.eWriteNames(npt.handle, numFrames, aNames, aValues, -1);
    
    t2 = now;
    disp([' done (' num2str(round((t2-t1)*60*60*24,3)) 's)']);

end


%% Initialize Figure

%% Define Callbacks


end
