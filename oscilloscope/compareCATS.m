function compareCATS(files)


if nargin ~= 1
    files = {'X:\LabJackLogs\CATS\2023\2023.08\08.25\CATS_2023-08-25_12-32-56.mat'};
        files = {'X:\LabJackLogs\CATS\2023\2023.08\08.29\CATS_2023-08-29_14-19-35.mat'};

%     
%      mydir = uigetdir;
%      fs = dir([mydir filesep '*.mat']);
%      names = {fs.name};
%      names = sort(names);
%      inds = contains(names,'extra');
%      names(inds)=[];    
%      files = fullfile(mydir,names);
end

tlim = [4 11]; % time limits
vlim = [-5.5 6]; % voltage limits
rlim = [-.5 1.5]; % Residue limit

% tlim = [5.7 8]; % time limits
% vlim = [0 4]; % voltage limits
% rlim = [-.05 1]; % Residue limit
%% Settings
myc={'#E6194B', '#3CB44B', '#ffe119', '#4363d8', '#f58231', '#911eb4', ...
     '#42d4f4', '#bfef45', '#fabed4', '#469990', '#dcbeff', ...
     '#9A6324', '#800000', '#aaffc3', '#808000',  ...
     '#000075', '#000000','#ffffff'};
 
% Channels to look at
chnames = {'Push Coil','MOT Coil','Coil 3','Coil 4','Coil 5',...
    'Coil 6','Coil 7','Coil 8','Coil 9','Coil 10','Coil 11','Coil 12a',...
    'Coil 12b','Coil 13','Coil 14','Coil 15','Coil 16','kitten'};

%% Calibratin Functions

monV2curr_12a = @(V) (V-0.0018)/0.1177;
monV2curr_12b = @(V) (V-0.0137)/0.1253;
monV2curr_13 = @(V) (V-0.0109)/0.1249;
monV2curr_14 = @(V) (V-.004)/0.123;
monV2curr_15 = @(V) (V-0.0134)/0.1195;
monV2curr_16 = @(V) (V-0.0019)/0.1208;
monV2curr_k = @(V) (V-0.0011)/0.1211;


adwinV2curr_12a = @(V) V*7.8427-0.6988;
adwinV2curr_12b = @(V) (V*7.971-0.8378).*((V*7.971-0.8378)>=0) + ...
    (V*8.0626+0.7314).*((V*8.0626+0.7314)<=0);
adwinV2curr_13 = @(V) (V*7.9464-0.737).*((V*7.9464-0.737)>=0) + ...
    (V*8.0184+0.8538).*((V*8.0184+0.8538)<=0);
adwinV2curr_14 = @(V) (V*7.9498-0.7872).*((V*7.9498-0.7872)>=0) + ...
    (V*8.0155+0.7975).*((V*8.0155+0.7975)<=0);

adwinV2curr_15 = @(V) (V*7.4974-0.935).*((V*7.4974-0.935)>=0);
adwinV2curr_16 = @(V) (V*7.6886-0.6687).*((V*7.6886-0.6687)>=0);
adwinV2curr_k = @(V) (V*7.775-2.4746).*((V*7.775-2.4746)>=0);
doCalibrate=1;
%%
vffs = zeros(length(files),1);
err12a = zeros(length(files),1);
err12b = zeros(length(files),1);

err13 = zeros(length(files),1);
err14 = zeros(length(files),1);
err15 = zeros(length(files),1);
err16 = zeros(length(files),1);
errk = zeros(length(files),1);

for nn=1:length(files)
    filename = files{nn};
    [path,fname,ext] = fileparts(filename);
    
    adwin_file = fullfile(path,[fname '_extra.mat']);
    
   if ~exist(filename) || ~exist(adwin_file)
      continue 
   end
   
   d1 = load(filename);
   d2 = load(adwin_file);
   
   t=d2.aTraces(14).data(:,1);
   v =d2.aTraces(14).data(:,2);
    % Remove duplicates
    [b,m1,n1] = unique(t,'last');
    [~,inds] =sort(m1);
    t = b(inds);
    v = v(inds);    
    vff = interp1(t,v,7.654);
    vffs(nn) = vff*6.6;

   % Calculate offset time using the trigger
    i1=find(d2.dTraces(7).data(:,2)==1,1);
    t1 = d2.dTraces(7).data(i1,1);
    i1=find(d1.data(:,19)==1,1);
    t2=d1.t(i1);

    hF = figure(1000+nn);clf;
    set(hF,'windowstyle','docked');
    tcl = tiledlayout(3,1);
    legStrs1={};
    legStrsAdwin={};

    % Measured Data plot
    nexttile(tcl)
    for kk=1:size(d1.data,2)
        tRaw = d1.t;

        tShifted = d1.t+(t1-t2);
        y = d1.data(:,kk);
        
%         strrep(d1.InputNames(kk,:),' ','')
        if doCalibrate
            switch strrep(d1.InputNames(kk,:),' ','')
                case 'Coil12A'
                    y = monV2curr_12a(y);
                case 'Coil12B'
                    y = monV2curr_12b(y);
                case 'Coil13'
                    y = monV2curr_13(y);  
                case 'Coil14'
                    y = monV2curr_14(y);  
                case 'Coil15'
                    y = monV2curr_15(y);  
                case 'Coil16'
                    y = monV2curr_16(y);
                case 'Kitten'
                    y = monV2curr_k(y);
                case 'Coil15Direct'                    
                    y = 1e3*(y/50)- mean(y(50:100));
                case 'Coil16Direct'
                    y = 1e3*(y/50) - mean(y(50:100));
                case  'KittenDirect'
                    y = 1e3*(y/50)- mean(y(50:100));
            end
        end
        mycolor = myc{mod(kk-1,length(myc))+1};
        plot(tShifted,y,'color',mycolor,'linewidth',2);
        hold on    
        legStrs1{kk}=d1.InputNames(kk,:);   
    end

    
    if doCalibrate
        ylim(8*vlim);
        ylabel('monitor current (A)');
    else
        ylim(vlim);
        ylabel('monitor voltage (V)');
    end
    xlim(tlim);

    set(gca,'color',[.8 .8 .8]);
    title(['measured ' fname],'interpreter','none');
    xlabel('time (s)');

    % Adwin Requet Plot
    nexttile(tcl)
    clear ps
    cla
    strs2={};
    for kk=1:length(chnames)
        ind = find(ismember({d2.aTraces.name},chnames{kk}),1);
        a = d2.aTraces(ind);
        tAdwin = a.data(:,1);
        yAdwin = a.data(:,2);
        
        if doCalibrate

            switch a.name
                case 'Coil 12a'
                    yAdwin = adwinV2curr_12a(yAdwin);
                case 'Coil 12b'
                    yAdwin = adwinV2curr_12b(yAdwin);
                case 'Coil 13'
                    yAdwin = adwinV2curr_13(yAdwin);            
                case 'Coil 14'
                    yAdwin = adwinV2curr_14(yAdwin);            
                case 'Coil 15'
                    yAdwin = adwinV2curr_15(yAdwin);            
                case 'Coil 16'
                    yAdwin = adwinV2curr_16(yAdwin);
                case 'kitten'
                    yAdwin = adwinV2curr_k(yAdwin);
            end
        end
        
        mycolor = myc{mod(kk-1,length(myc))+1};
        ps(kk)=stairs(tAdwin,yAdwin,'color',mycolor,'linewidth',2);
        hold on    
        legStrsAdwin{kk}=a.name;

        
    end
    xlim([d1.t(1) d1.t(end)]);

    % Plot the trigger
    ps(end+1)=stairs(d2.dTraces(7).data(:,1),d2.dTraces(7).data(:,2),...
        'color',myc{1},'linewidth',2);
    legStrsAdwin{end+1}='Trigger';

    % Plot the feed forward
    ind = find(ismember({d2.aTraces.name},'Transport FF'),1);
    a = d2.aTraces(ind);
    ps(end+1)=plot(a.data(:,1),a.data(:,2),'k:','linewidth',2);    
    legStrsAdwin{end+1}=a.name;

    % Finish it
    if doCalibrate
        ylim(8*vlim);
        ylabel('adwin current (A)');
    else
        ylim(vlim);
        ylabel('adwin voltage (V)');        
    end
    xlim(tlim);

    set(gca,'color',[.8 .8 .8]);
    title(['adwin ' fname '_extra.mat'],'interpreter','none');
    xlabel('time (s)');
    hL = legend(ps,legStrsAdwin,'location','eastoutside'); 
    

    % Residu plot
    nexttile(tcl)
    for kk=1:length(chnames)
        ind = find(ismember({d2.aTraces.name},chnames{kk}),2);
        a = d2.aTraces(ind);    
        % Adwin
        x2 = a.data(:,1);
        y2 = a.data(:,2);  
        % Measured
        x1 = d1.t+(t1-t2);
        y1 = d1.data(:,kk);        
        
        if doCalibrate
            switch  a.name
                case 'Coil 12a'
                    y2 = adwinV2curr_12a(y2);
                    y1 = monV2curr_12a(y1);
                case 'Coil 12b'
                    y2 = adwinV2curr_12b(y2);
                    y1 = monV2curr_12b(y1);
                case 'Coil 13'
                    y2 = adwinV2curr_13(y2);       
                    y1 = monV2curr_13(y1);
                case 'Coil 14'
                    y2 = adwinV2curr_14(y2);   
                    y1 = monV2curr_14(y1);
                case 'Coil 15'
                    y2 = adwinV2curr_15(y2);    
                    y1 = monV2curr_15(y1);
                case 'Coil 16'
                    y2 =adwinV2curr_16(y2);
                    y1 = monV2curr_16(y1);
                case 'kitten'
                    y2 = adwinV2curr_k(y2);
                    y1 = monV2curr_k(y1);

            end
        end        
        
        % Remove duplicates
        [b,m1,n1] = unique(x2,'last');
        [~,inds] =sort(m1);
        x2 = b(inds);
        y2 = y2(inds);    
        % Inerpolation
        xq=linspace(tlim(1),tlim(2),1e4);
        y2_interp =  interp1(x2,y2,xq,'previous');
        y1_interp =  interp1(x1,y1,xq,'previous');    
        dy = y2_interp-y1_interp;        
        dy(isnan(dy))=0;
        
        sse = sum(dy.^2);
        
         switch  a.name
                case 'Coil 12a'
                    err12a(nn) = sse;                    
                case 'Coil 12b'
                    err12b(nn) = sse;     
                case 'Coil 13'
                    err13(nn) = sse;  
                case 'Coil 14'
                    err14(nn) = sse;   
                case 'Coil 15'
                    err15(nn) = sse;
                case 'Coil 16'
                    err16(nn) = sse;
                case 'kitten'
                    errk(nn) = sse;   
         end
            
        
        plot(xq,dy,'color',myc{mod(kk-1,length(myc))+1},'linewidth',2);
        hold on
    end
    xlim(tlim);
    if doCalibrate
        ylim(rlim*8);
        ylabel('adwin - monitor (A)');

    else
        ylim(rlim);
        ylabel('voltage (V)');

    end
    set(gca,'color',[.8 .8 .8]);
    title('residue');
    xlabel('time (s)');    
    drawnow;
    disp([num2str(nn) 'displayed']);
end


end

