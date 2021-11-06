function [positive, negative, all] = findAllPeaks(signal,absciss,varargin)
%FINDALLPEAKS Summary of this function goes here
%   [positive, negative, all] = FINDALLPEAKS(Y,X) specifies X as the location vector of data
%   vector Y. X must be a strictly increasing vector of the same length as
%   Y. LOCS returns the corresponding value of X for each peak detected.
%   If X is omitted, then X will correspond to the indices of Y.
%
%   [positive, negative, all] = FINDALLPEAKS(Y,X,OPTIONS) specifies X as the location vector of data
%   vector Y. X must be a strictly increasing vector of the same length as
%   Y. LOCS returns the corresponding value of X for each peak detected.
%   If X is omitted, then X will correspond to the indices of Y.
%   options is an optional struct with logic fields includeInitialPeak and 
%   includeFinalPeak. 

initialArgs = 2;
remainingArgs = nargin - initialArgs;
switch remainingArgs
    case 0
        options = struct('includeInitialPeak', false,...
                'includeFinalPeak', false);
    case 1
        options = varargin{1};
    otherwise
        error('Too many input parameters');
end
[peak_pos,location_pos,width_pos,prominence_pos] = findpeaks(signal,absciss);
base_pos = peak_pos - prominence_pos;
[peak_neg,location_neg,width_neg,prominence_neg] = findpeaks(-signal,absciss);
base_neg = prominence_neg - peak_neg;
 
negLength = numel(peak_neg);
posLength = numel(peak_pos);
allLength = negLength + posLength;

negative = getStructure(-peak_neg,location_neg,width_neg,prominence_neg, base_neg);
positive = getStructure(peak_pos,location_pos,width_pos,prominence_pos, base_pos);
allUnsorted = [negative; positive];
[~,idx]=sort([allUnsorted.location]);
all = allUnsorted(idx);

mode = posLength > negLength;
isNegativeArray = num2cell(isNegative(1:allLength, mode));
[all.isNegative] = isNegativeArray{:};
for i = 1:allLength
    switch i
        case 1
            currentPeak = all(1);
            initialPeak = struct(...
                'peak',signal(1),...
                'location',absciss(1),...
                'width',currentPeak.location,...
                'prominence',abs(signal(1)-currentPeak.peak),...
                'base', currentPeak.peak,...
                'isNegative', ~currentPeak.isNegative);
            adjacentPeaks = [initialPeak all(2)];
        case allLength
            previousPeak = all(allLength-1);
            currentPeak = all(allLength);
            finalPeak = struct(...
                'peak',signal(allLength),...
                'location',absciss(end),...
                'width',currentPeak.location,...
                'prominence',abs(signal(allLength)-currentPeak.peak),...
                'base', currentPeak.peak,...
                'isNegative', ~currentPeak.isNegative);            
            adjacentPeaks = [previousPeak finalPeak];
        otherwise
            adjacentPeaks = [all(i-1) all(i+1)];
    end
    all(i).prominence = min(abs([adjacentPeaks.peak] - all(i).peak));
    switch all(i).isNegative
        case false
            all(i).base = all(i).peak - all(i).prominence;
        % case true
        otherwise
            all(i).base = all(i).peak + all(i).prominence;
    end
end
if (options.includeInitialPeak)
    all = [initialPeak; all];
end
if (options.includeFinalPeak)
    all = [all; finalPeak];
end
prominenceRatioArray = num2cell([all.prominence]./[all.base]);
[all.prominenceRatio] = prominenceRatioArray{:};
negative=all([all.isNegative]);
positive=all(~[all.isNegative]);

function st = getStructure(peak,location,width,prominence,base)
peak = peak';
location = location';
width = width';
prominence = prominence';
base = base';
t = table(peak,location,width,prominence,base);
st = table2struct(t);

function res = isNegative(i, mode)
res = xor(mod(i,2), mode);